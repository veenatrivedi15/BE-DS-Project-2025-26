// import React from 'react';
// import {
//   View,
//   StyleSheet,
//   Alert,
//   Text,
//   TextInput,
//   TouchableOpacity,
// } from 'react-native';
// import { SafeAreaView } from 'react-native-safe-area-context';
// import { router } from 'expo-router';
// import { useAuth } from '../contexts/AuthContext';
// import { Ionicons } from '@expo/vector-icons';

// export default function SignUpScreen() {
//   const [email, setEmail] = React.useState('');
//   const [password, setPassword] = React.useState('');
//   const [confirmPassword, setConfirmPassword] = React.useState('');
//   const [loading, setLoading] = React.useState(false);
//   const { signUp } = useAuth();

//   const handleSignUp = async () => {
//     if (!email || !password || !confirmPassword) {
//       Alert.alert('Error', 'Please fill in all fields');
//       return;
//     }

//     if (password !== confirmPassword) {
//       Alert.alert('Error', 'Passwords do not match');
//       return;
//     }

//     if (password.length < 6) {
//       Alert.alert('Error', 'Password must be at least 6 characters');
//       return;
//     }

//     setLoading(true);
//    try {
//       await signUp(email, password);
//       router.replace('/dashboard');
//     } catch (error) {
//       let message = 'Sign Up Failed';
//       if (error && typeof error === 'object' && 'message' in error) {
//         message = (error as { message: string }).message;
//       }
//       Alert.alert('Sign Up Failed', message);
//     } finally {
//       setLoading(false);
//     }
//   };

//   return (
//     <SafeAreaView style={styles.container}>
//       <View style={styles.content}>
//         <View style={styles.header}>
//           <Ionicons name="water" size={80} color="#4CAF50" />
//           <Text style={styles.title}>Create Account</Text>
//           <Text style={styles.subtitle}>
//             Join Smart Irrigation System
//           </Text>
//         </View>

//         <View style={styles.card}>
//           <View style={styles.inputContainer}>
//             <Ionicons name="mail" size={20} color="#666" style={styles.inputIcon} />
//             <TextInput
//               style={styles.textInput}
//               placeholder="Email"
//               value={email}
//               onChangeText={setEmail}
//               keyboardType="email-address"
//               autoCapitalize="none"
//               placeholderTextColor="#999"
//             />
//           </View>

//           <View style={styles.inputContainer}>
//             <Ionicons name="lock-closed" size={20} color="#666" style={styles.inputIcon} />
//             <TextInput
//               style={styles.textInput}
//               placeholder="Password"
//               value={password}
//               onChangeText={setPassword}
//               secureTextEntry
//               placeholderTextColor="#999"
//             />
//           </View>

//           <View style={styles.inputContainer}>
//             <Ionicons name="checkmark-circle" size={20} color="#666" style={styles.inputIcon} />
//             <TextInput
//               style={styles.textInput}
//               placeholder="Confirm Password"
//               value={confirmPassword}
//               onChangeText={setConfirmPassword}
//               secureTextEntry
//               placeholderTextColor="#999"
//             />
//           </View>

//           <TouchableOpacity
//             style={[styles.button, loading && styles.buttonDisabled]}
//             onPress={handleSignUp}
//             disabled={loading}
//           >
//             <Text style={styles.buttonText}>
//               {loading ? 'Creating Account...' : 'Create Account'}
//             </Text>
//           </TouchableOpacity>

//           <TouchableOpacity
//             style={styles.linkButton}
//             onPress={() => router.push('/')}
//           >
//             <Text style={styles.linkText}>
//               Already have an account? Sign In
//             </Text>
//           </TouchableOpacity>
//         </View>
//       </View>
//     </SafeAreaView>
//   );
// }

// const styles = StyleSheet.create({
//   container: {
//     flex: 1,
//     backgroundColor: '#f5f5f5',
//   },
//   content: {
//     flex: 1,
//     padding: 20,
//     justifyContent: 'center',
//   },
//   header: {
//     alignItems: 'center',
//     marginBottom: 30,
//   },
//   title: {
//     fontSize: 28,
//     fontWeight: 'bold',
//     color: '#2E7D32',
//     marginTop: 10,
//   },
//   subtitle: {
//     fontSize: 16,
//     color: '#666',
//     textAlign: 'center',
//     marginTop: 5,
//   },
//   card: {
//     backgroundColor: 'white',
//     borderRadius: 12,
//     padding: 20,
//     shadowColor: '#000',
//     shadowOffset: {
//       width: 0,
//       height: 2,
//     },
//     shadowOpacity: 0.1,
//     shadowRadius: 4,
//     elevation: 3,
//   },
//   inputContainer: {
//     flexDirection: 'row',
//     alignItems: 'center',
//     borderWidth: 1,
//     borderColor: '#ddd',
//     borderRadius: 8,
//     marginBottom: 16,
//     paddingHorizontal: 12,
//     backgroundColor: 'white',
//   },
//   inputIcon: {
//     marginRight: 12,
//   },
//   textInput: {
//     flex: 1,
//     paddingVertical: 12,
//     fontSize: 16,
//     color: '#333',
//   },
//   button: {
//     backgroundColor: '#4CAF50',
//     paddingVertical: 15,
//     borderRadius: 8,
//     alignItems: 'center',
//     marginTop: 8,
//   },
//   buttonDisabled: {
//     backgroundColor: '#ccc',
//   },
//   buttonText: {
//     color: 'white',
//     fontSize: 16,
//     fontWeight: 'bold',
//   },
//   linkButton: {
//     marginTop: 16,
//     alignItems: 'center',
//   },
//   linkText: {
//     color: '#4CAF50',
//     fontSize: 14,
//   },
// });



import React from 'react';
import {
  View,
  StyleSheet,
  Alert,
  Text,
  TextInput,
  TouchableOpacity,
  ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { useAuth } from '../contexts/AuthContext';
import { Ionicons } from '@expo/vector-icons';

export default function SignUpScreen() {
  const [email, setEmail] = React.useState('');
  const [password, setPassword] = React.useState('');
  const [confirmPassword, setConfirmPassword] = React.useState('');
  const [loading, setLoading] = React.useState(false);
  const [showPassword, setShowPassword] = React.useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = React.useState(false);
  const { signUp } = useAuth();

  const handleSignUp = async () => {
    console.log('📍 [SIGNUP SCREEN] handleSignUp called');
    
    if (!email || !password || !confirmPassword) {
      Alert.alert('Error', 'Please fill in all fields');
      return;
    }

    console.log('📍 [SIGNUP SCREEN] Email:', email);
    console.log('📍 [SIGNUP SCREEN] Password length:', password.length);
    console.log('📍 [SIGNUP SCREEN] Passwords match:', password === confirmPassword);

    // Email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      Alert.alert('Error', 'Please enter a valid email address');
      return;
    }

    if (password !== confirmPassword) {
      Alert.alert('Error', 'Passwords do not match');
      return;
    }

    if (password.length < 6) {
      Alert.alert('Error', 'Password must be at least 6 characters');
      return;
    }

    // Optional: Strong password check
    const hasUpperCase = /[A-Z]/.test(password);
    const hasLowerCase = /[a-z]/.test(password);
    const hasNumber = /[0-9]/.test(password);
    
    if (!hasUpperCase || !hasLowerCase || !hasNumber) {
      Alert.alert(
        'Weak Password',
        'For better security, password should contain:\n• Uppercase letter\n• Lowercase letter\n• Number\n\nContinue anyway?',
        [
          { text: 'Change Password', style: 'cancel' },
          { text: 'Continue', onPress: () => proceedWithSignUp() }
        ]
      );
      return;
    }

    console.log('📍 [SIGNUP SCREEN] All validations passed, calling proceedWithSignUp');
    await proceedWithSignUp();
  };

  const proceedWithSignUp = async () => {
    console.log('📍 [SIGNUP SCREEN] proceedWithSignUp called');
    console.log('📍 [SIGNUP SCREEN] signUp function type:', typeof signUp);
    
    setLoading(true);
    try {
      console.log('📍 [SIGNUP SCREEN] About to call signUp with:', email.trim());
      await signUp(email.trim(), password);
      console.log('📍 [SIGNUP SCREEN] signUp completed successfully');
      // Navigation handled by AuthContext
    } catch (error) {
      console.log('📍 [SIGNUP SCREEN] signUp failed:', error);
      let message = 'Sign Up Failed';
      if (error && typeof error === 'object' && 'message' in error) {
        message = (error as { message: string }).message;
      }
      Alert.alert('Sign Up Failed', message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        <View style={styles.header}>
          <TouchableOpacity 
            onPress={() => router.back()} 
            style={styles.backButton}
            disabled={loading}
          >
            <Ionicons name="arrow-back" size={24} color="#4CAF50" />
          </TouchableOpacity>
          <Ionicons name="water" size={80} color="#4CAF50" />
          <Text style={styles.title}>Create Account</Text>
          <Text style={styles.subtitle}>
            Join Smart Irrigation System
          </Text>
        </View>

        <View style={styles.card}>
          <View style={styles.inputContainer}>
            <Ionicons name="mail" size={20} color="#666" style={styles.inputIcon} />
            <TextInput
              style={styles.textInput}
              placeholder="Email"
              value={email}
              onChangeText={setEmail}
              keyboardType="email-address"
              autoCapitalize="none"
              autoComplete="email"
              placeholderTextColor="#999"
              editable={!loading}
            />
          </View>

          <View style={styles.inputContainer}>
            <Ionicons name="lock-closed" size={20} color="#666" style={styles.inputIcon} />
            <TextInput
              style={styles.textInput}
              placeholder="Password (min 6 characters)"
              value={password}
              onChangeText={setPassword}
              secureTextEntry={!showPassword}
              autoComplete="password-new"
              placeholderTextColor="#999"
              editable={!loading}
            />
            <TouchableOpacity
              onPress={() => setShowPassword(!showPassword)}
              style={styles.eyeIcon}
              disabled={loading}
            >
              <Ionicons 
                name={showPassword ? "eye-off" : "eye"} 
                size={20} 
                color="#666" 
              />
            </TouchableOpacity>
          </View>

          <View style={styles.inputContainer}>
            <Ionicons name="checkmark-circle" size={20} color="#666" style={styles.inputIcon} />
            <TextInput
              style={styles.textInput}
              placeholder="Confirm Password"
              value={confirmPassword}
              onChangeText={setConfirmPassword}
              secureTextEntry={!showConfirmPassword}
              autoComplete="password-new"
              placeholderTextColor="#999"
              editable={!loading}
            />
            <TouchableOpacity
              onPress={() => setShowConfirmPassword(!showConfirmPassword)}
              style={styles.eyeIcon}
              disabled={loading}
            >
              <Ionicons 
                name={showConfirmPassword ? "eye-off" : "eye"} 
                size={20} 
                color="#666" 
              />
            </TouchableOpacity>
          </View>

          <View style={styles.passwordHint}>
            <Text style={styles.hintText}>
              💡 Tip: Use uppercase, lowercase, and numbers
            </Text>
          </View>

          <TouchableOpacity
            style={[styles.button, loading && styles.buttonDisabled]}
            onPress={handleSignUp}
            disabled={loading}
          >
            {loading ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.buttonText}>Create Account</Text>
            )}
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.linkButton}
            onPress={() => router.push('/')}
            disabled={loading}
          >
            <Text style={styles.linkText}>
              Already have an account? <Text style={styles.linkTextBold}>Sign In</Text>
            </Text>
          </TouchableOpacity>
        </View>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  content: {
    flex: 1,
    padding: 20,
    justifyContent: 'center',
  },
  header: {
    alignItems: 'center',
    marginBottom: 30,
    position: 'relative',
  },
  backButton: {
    position: 'absolute',
    left: 0,
    top: 0,
    padding: 8,
    zIndex: 1,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#2E7D32',
    marginTop: 10,
  },
  subtitle: {
    fontSize: 16,
    color: '#666',
    textAlign: 'center',
    marginTop: 5,
  },
  card: {
    backgroundColor: 'white',
    borderRadius: 12,
    padding: 20,
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 8,
    marginBottom: 16,
    paddingHorizontal: 12,
    backgroundColor: 'white',
  },
  inputIcon: {
    marginRight: 12,
  },
  textInput: {
    flex: 1,
    paddingVertical: 12,
    fontSize: 16,
    color: '#333',
  },
  eyeIcon: {
    padding: 4,
  },
  passwordHint: {
    marginBottom: 16,
    marginTop: -8,
  },
  hintText: {
    fontSize: 12,
    color: '#999',
    textAlign: 'center',
  },
  button: {
    backgroundColor: '#4CAF50',
    paddingVertical: 15,
    borderRadius: 8,
    alignItems: 'center',
    marginTop: 8,
  },
  buttonDisabled: {
    backgroundColor: '#A5D6A7',
  },
  buttonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: 'bold',
  },
  linkButton: {
    marginTop: 16,
    alignItems: 'center',
  },
  linkText: {
    color: '#666',
    fontSize: 14,
  },
  linkTextBold: {
    color: '#4CAF50',
    fontWeight: 'bold',
  },
});