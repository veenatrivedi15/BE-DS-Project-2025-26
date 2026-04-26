// import React from 'react';
// import { View, StyleSheet, Text, TouchableOpacity, Alert, TextInput } from 'react-native';
// import { SafeAreaView } from 'react-native-safe-area-context';
// import { router } from 'expo-router';
// import { Ionicons } from '@expo/vector-icons';
// import { useAuth } from '../contexts/AuthContext';

// export default function LoginScreen() {
//   const [email, setEmail] = React.useState('');
//   const [password, setPassword] = React.useState('');
//   const [loading, setLoading] = React.useState(false);
//   const { signIn, user } = useAuth();

//   // If user is already logged in, redirect to dashboard
//   React.useEffect(() => {
//     if (user) {
//       router.replace('/dashboard');
//     }
//   }, [user]);

//   const handleLogin = async () => {
//     if (!email || !password) {
//       Alert.alert('Error', 'Please fill in all fields');
//       return;
//     }

//     setLoading(true);
//      try {
//       await signIn(email, password);
//       router.replace('/dashboard');
//     } catch (error) {
//       let message = 'Login Failed';
//       if (error && typeof error === 'object' && 'message' in error) {
//         message = (error as { message: string }).message;
//       }
//       Alert.alert('Login Failed', message);
//     } finally {
//       setLoading(false);
//     }
//   };

//   return (
//     <SafeAreaView style={styles.container}>
//       <View style={styles.content}>
//         <View style={styles.header}>
//           <Ionicons name="water" size={80} color="#4CAF50" />
//           <Text style={styles.title}>Smart Irrigation</Text>
//           <Text style={styles.subtitle}>
//             Monitor and control your irrigation system
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

//           <TouchableOpacity
//             style={[styles.button, loading && styles.buttonDisabled]}
//             onPress={handleLogin}
//             disabled={loading}
//           >
//             <Text style={styles.buttonText}>
//               {loading ? 'Signing In...' : 'Sign In'}
//             </Text>
//           </TouchableOpacity>

//           <TouchableOpacity
//             style={styles.linkButton}
//             onPress={() => router.push('/signup')}
//           >
//             <Text style={styles.linkText}>
//               Don't have an account? Sign Up
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
import { View, StyleSheet, Text, TouchableOpacity, Alert, TextInput, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../contexts/AuthContext';

export default function LoginScreen() {
  const [email, setEmail] = React.useState('');
  const [password, setPassword] = React.useState('');
  const [loading, setLoading] = React.useState(false);
  const { signIn, user } = useAuth();

  // If user is already logged in, redirect to dashboard
  React.useEffect(() => {
    if (user) {
      router.replace('/dashboard');
    }
  }, [user]);

  const handleLogin = async () => {
    if (!email || !password) {
      Alert.alert('Error', 'Please fill in all fields');
      return;
    }

    // Basic email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      Alert.alert('Error', 'Please enter a valid email address');
      return;
    }

    setLoading(true);
    try {
      await signIn(email.trim(), password);
      // Navigation handled by AuthContext
    } catch (error) {
      let message = 'Login Failed';
      if (error && typeof error === 'object' && 'message' in error) {
        message = (error as { message: string }).message;
      }
      Alert.alert('Login Failed', message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        <View style={styles.header}>
          <Ionicons name="water" size={80} color="#4CAF50" />
          <Text style={styles.title}>Smart Irrigation</Text>
          <Text style={styles.subtitle}>
            Monitor and control your irrigation system
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
              placeholder="Password"
              value={password}
              onChangeText={setPassword}
              secureTextEntry
              autoComplete="password"
              placeholderTextColor="#999"
              editable={!loading}
            />
          </View>

          <TouchableOpacity
            style={[styles.button, loading && styles.buttonDisabled]}
            onPress={handleLogin}
            disabled={loading}
          >
            {loading ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.buttonText}>Sign In</Text>
            )}
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.linkButton}
            onPress={() => router.push('/signup')}
            disabled={loading}
          >
            <Text style={styles.linkText}>
              Don't have an account? <Text style={styles.linkTextBold}>Sign Up</Text>
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