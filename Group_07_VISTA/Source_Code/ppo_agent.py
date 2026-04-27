import numpy as np
import tensorflow as tf
from keras import layers, Model, optimizers

class PPOBuffer:
    def __init__(self, size, obs_shape, act_dim):
        self.traffic_state_buf = np.zeros((size, 12, 5), dtype=np.float32)
        self.phase_index_buf = np.zeros((size, 8), dtype=np.float32)
        self.phase_buf = np.zeros((size,), dtype=np.int32)
        self.duration_buf = np.zeros((size, 1), dtype=np.float32)
        self.adv_buf = np.zeros(size, dtype=np.float32)
        self.rew_buf = np.zeros(size, dtype=np.float32)
        self.ret_buf = np.zeros(size, dtype=np.float32)
        self.val_buf = np.zeros(size, dtype=np.float32)
        self.logp_phase_buf = np.zeros(size, dtype=np.float32)
        self.logp_duration_buf = np.zeros(size, dtype=np.float32)
        self.ptr, self.path_start_idx, self.max_size = 0, 0, size

    def store(self, obs, phase, duration, reward, value, logp_phase, logp_duration):
        assert self.ptr < self.max_size
        self.traffic_state_buf[self.ptr] = obs[0]
        self.phase_index_buf[self.ptr] = obs[1]
        self.phase_buf[self.ptr] = phase
        self.duration_buf[self.ptr] = duration
        self.rew_buf[self.ptr] = reward
        self.val_buf[self.ptr] = value
        self.logp_phase_buf[self.ptr] = logp_phase
        self.logp_duration_buf[self.ptr] = logp_duration
        self.ptr += 1

    def finish_path(self, last_val=0, gamma=0.99, lam=0.95):
        path_slice = slice(self.path_start_idx, self.ptr)
        rews = np.append(self.rew_buf[path_slice], last_val)
        vals = np.append(self.val_buf[path_slice], last_val)
        adv = np.zeros_like(rews[:-1])
        lastgaelam = 0
        for t in reversed(range(len(rews)-1)):
            delta = rews[t] + gamma * vals[t+1] - vals[t]
            adv[t] = lastgaelam = delta + gamma * lam * lastgaelam
        self.adv_buf[path_slice] = adv
        self.ret_buf[path_slice] = adv + self.val_buf[path_slice]
        self.path_start_idx = self.ptr

    def get(self):
        # Return only the filled portion of the buffer so training can proceed
        size = self.ptr
        if size == 0:
            raise ValueError("Buffer is empty")
        traffic_state = self.traffic_state_buf[:size]
        phase_index = self.phase_index_buf[:size]
        phase = self.phase_buf[:size]
        duration = self.duration_buf[:size]
        ret = self.ret_buf[:size]
        adv = self.adv_buf[:size]
        logp_phase = self.logp_phase_buf[:size]
        logp_duration = self.logp_duration_buf[:size]
        # normalize advantages
        adv_mean, adv_std = np.mean(adv), np.std(adv)
        adv_norm = (adv - adv_mean) / (adv_std + 1e-8)
        # reset pointers for next use
        self.ptr, self.path_start_idx = 0, 0
        return [traffic_state, phase_index, phase, duration, ret, adv_norm, logp_phase, logp_duration]

class PPOActor(Model):
    def __init__(self, state_shape, phase_dim):
        self.traffic_input = layers.Input(shape=state_shape[0])
        self.phase_input = layers.Input(shape=state_shape[1])
        x1 = layers.Dense(50, activation='relu')(self.traffic_input)
        x1 = layers.Dense(30, activation='relu')(x1)
        x1 = layers.Flatten()(x1)
        x2 = layers.Dense(20, activation='relu')(self.phase_input)
        x = layers.concatenate([x1, x2])
        x = layers.Dense(32, activation='relu')(x)
        phase_logits = layers.Dense(phase_dim, name='phase_logits')(x)
        duration_mu = layers.Dense(1, activation='sigmoid', name='duration_mu')(x)
        self.duration_logstd = tf.Variable(initial_value=-0.5*np.ones(1, dtype=np.float32), trainable=True, name='duration_logstd')
        super().__init__(inputs=[self.traffic_input, self.phase_input], outputs=[phase_logits, duration_mu])

    def call(self, inputs):
        phase_logits, duration_mu = super().call(inputs)
        return phase_logits, duration_mu, self.duration_logstd

class PPOCritic(Model):
    def __init__(self, state_shape):
        self.traffic_input = layers.Input(shape=state_shape[0])
        self.phase_input = layers.Input(shape=state_shape[1])
        x1 = layers.Dense(50, activation='relu')(self.traffic_input)
        x1 = layers.Dense(30, activation='relu')(x1)
        x1 = layers.Flatten()(x1)
        x2 = layers.Dense(20, activation='relu')(self.phase_input)
        x = layers.concatenate([x1, x2])
        x = layers.Dense(32, activation='relu')(x)
        value = layers.Dense(1, name='value')(x)
        super().__init__(inputs=[self.traffic_input, self.phase_input], outputs=value)

    def call(self, inputs):
        value = super().call(inputs)
        return value

class PPOAgent:
    def __init__(self, state_shape, phase_dim, duration_range=(5, 60), gamma=0.99, lam=0.95, clip_ratio=0.2, pi_lr=3e-4, vf_lr=1e-3):
        self.state_shape = state_shape
        self.phase_dim = phase_dim
        self.duration_range = duration_range
        self.gamma = gamma
        self.lam = lam
        self.clip_ratio = clip_ratio
        self.actor = PPOActor(state_shape, phase_dim)
        self.critic = PPOCritic(state_shape)
        self.pi_optimizer = optimizers.Adam(learning_rate=pi_lr)
        self.vf_optimizer = optimizers.Adam(learning_rate=vf_lr)

    def get_action(self, state):
        traffic_state, phase_index = state
        phase_logits, duration_mu, duration_logstd = self.actor([traffic_state, phase_index])
        phase_probs = tf.nn.softmax(phase_logits)
        phase_dist = tf.squeeze(phase_probs)
        phase = np.random.choice(self.phase_dim, p=phase_dist.numpy())
        logp_phase = np.log(phase_dist[phase] + 1e-8)
        duration_std = tf.exp(duration_logstd)
        duration = duration_mu + duration_std * tf.random.normal(shape=(1,))
        duration = tf.clip_by_value(duration, 0, 1)
        logp_duration = -0.5 * ((duration - duration_mu) / (duration_std + 1e-8))**2 - tf.math.log(duration_std + 1e-8) - 0.5 * np.log(2 * np.pi)
        duration_steps = int(self.duration_range[0] + duration.numpy()[0] * (self.duration_range[1] - self.duration_range[0]))
        value = self.critic([traffic_state, phase_index])
        value_scalar = float(value.numpy()[0,0]) if hasattr(value, 'numpy') else float(value[0,0])
        logp_phase_scalar = float(logp_phase)
        logp_duration_scalar = float(logp_duration.numpy()[0]) if hasattr(logp_duration, 'numpy') else float(logp_duration[0])
        return phase, duration_steps, value_scalar, logp_phase_scalar, logp_duration_scalar

    def update(self, buf, train_pi_iters=80, train_v_iters=80, target_kl=0.01):
        traffic_state_buf, phase_index_buf, phase_buf, duration_buf, ret_buf, adv_buf, logp_phase_buf, logp_duration_buf = buf.get()
        # Policy (actor) update
        for i in range(train_pi_iters):
            with tf.GradientTape() as tape:
                phase_logits, duration_mu, duration_logstd = self.actor([traffic_state_buf, phase_index_buf])
                phase_probs = tf.nn.softmax(phase_logits)
                phase_onehot = tf.one_hot(phase_buf, self.phase_dim)
                phase_prob = tf.reduce_sum(phase_probs * phase_onehot, axis=1)
                logp_phase = tf.math.log(phase_prob + 1e-8)
                ratio_phase = tf.exp(logp_phase - logp_phase_buf)
                min_adv_phase = tf.where(adv_buf > 0, (1 + self.clip_ratio) * adv_buf, (1 - self.clip_ratio) * adv_buf)
                phase_loss = -tf.reduce_mean(tf.minimum(ratio_phase * adv_buf, min_adv_phase))
                duration_std = tf.exp(duration_logstd)
                logp_duration = -0.5 * ((duration_buf - duration_mu) / (duration_std + 1e-8))**2 - tf.math.log(duration_std + 1e-8) - 0.5 * np.log(2 * np.pi)
                ratio_duration = tf.exp(logp_duration - logp_duration_buf)
                min_adv_duration = tf.where(adv_buf > 0, (1 + self.clip_ratio) * adv_buf, (1 - self.clip_ratio) * adv_buf)
                duration_loss = -tf.reduce_mean(tf.minimum(ratio_duration * adv_buf, min_adv_duration))
                pi_loss = phase_loss + duration_loss
            actor_vars = self.actor.trainable_variables + [self.actor.duration_logstd]
            grads = tape.gradient(pi_loss, actor_vars)
            self.pi_optimizer.apply_gradients(zip(grads, actor_vars))
        # Value (critic) update
        for i in range(train_v_iters):
            with tf.GradientTape() as tape:
                value = self.critic([traffic_state_buf, phase_index_buf])
                v_loss = tf.reduce_mean((ret_buf - tf.squeeze(value))**2)
            grads = tape.gradient(v_loss, self.critic.trainable_variables)
            self.vf_optimizer.apply_gradients(zip(grads, self.critic.trainable_variables)) 