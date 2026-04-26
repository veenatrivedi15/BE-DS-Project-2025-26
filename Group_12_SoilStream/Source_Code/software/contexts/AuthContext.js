// import React, { createContext, useContext, useEffect, useState } from 'react';
// import { auth } from '../lib/firebase';

// const AuthContext = createContext({});

// export const useAuth = () => {
//   const context = useContext(AuthContext);
//   if (!context) {
//     throw new Error('useAuth must be used within an AuthProvider');
//   }
//   return context;
// };

// export const AuthProvider = ({ children }) => {
//   const [user, setUser] = useState(null);
//   const [loading, setLoading] = useState(true);

//   useEffect(() => {
//     const unsubscribe = auth.onAuthStateChanged((user) => {
//       setUser(user);
//       setLoading(false);
//     });

//     return unsubscribe;
//   }, []);

//   const signIn = async (email, password) => {
//     try {
//       const result = await auth.signInWithEmailAndPassword(email, password);
//       return result;
//     } catch (error) {
//       throw error;
//     }
//   };

//   const signUp = async (email, password) => {
//     try {
//       const result = await auth.createUserWithEmailAndPassword(email, password);
//       return result;
//     } catch (error) {
//       throw error;
//     }
//   };

//   const signOut = async () => {
//     try {
//       await auth.signOut();
//     } catch (error) {
//       throw error;
//     }
//   };

//   const value = {
//     user,
//     loading,
//     signIn,
//     signUp,
//     signOut
//   };

//   return (
//     <AuthContext.Provider value={value}>
//       {children}
//     </AuthContext.Provider>
//   );
// };


// contexts/AuthContext.js
// contexts/AuthContext.js
import React, { createContext, useState, useEffect, useContext } from 'react';
import { 
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  signOut,
  onAuthStateChanged,
  sendPasswordResetEmail,
  updateProfile
} from 'firebase/auth';
import { auth } from '../firebase/config';
import { router } from 'expo-router';

const AuthContext = createContext({});

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [initializing, setInitializing] = useState(true);

  // Monitor auth state changes
  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (user) => {
      console.log('Auth state changed:', user ? user.email : 'No user');
      setUser(user);
      
      if (initializing) {
        setInitializing(false);
      }
      setLoading(false);
    });

    return unsubscribe;
  }, []);

  // Sign up with email and password
  const signUp = async (email, password, displayName) => {
    try {
      setLoading(true);
      console.log('🔵 Attempting to sign up with email:', email);
      
      const userCredential = await createUserWithEmailAndPassword(auth, email, password);
      
      console.log('✅ Sign up successful:', userCredential.user.email);
      
      // Update display name if provided
      if (displayName && userCredential.user) {
        await updateProfile(userCredential.user, {
          displayName: displayName
        });
        console.log('✅ Display name updated:', displayName);
      }
      
      // Navigate to dashboard after successful signup
      router.replace('/dashboard');
      
      return userCredential.user;
    } catch (error) {
      console.error('❌ Sign up error:', error.code, error.message);
      throw handleAuthError(error);
    } finally {
      setLoading(false);
    }
  };

  // Sign in with email and password
  const signIn = async (email, password) => {
    try {
      setLoading(true);
      console.log('🔵 Attempting to sign in with email:', email);
      
      const userCredential = await signInWithEmailAndPassword(auth, email, password);
      
      console.log('✅ Sign in successful:', userCredential.user.email);
      
      // Navigate to dashboard after successful login
      router.replace('/dashboard');
      
      return userCredential.user;
    } catch (error) {
      console.error('❌ Sign in error:', error.code, error.message);
      throw handleAuthError(error);
    } finally {
      setLoading(false);
    }
  };

  // Sign out
  const logout = async () => {
    try {
      setLoading(true);
      await signOut(auth);
      console.log('User signed out');
      
      // Navigate to login screen
      router.replace('/');
    } catch (error) {
      console.error('Sign out error:', error);
      throw handleAuthError(error);
    } finally {
      setLoading(false);
    }
  };

  // Reset password
  const resetPassword = async (email) => {
    try {
      await sendPasswordResetEmail(auth, email);
      console.log('Password reset email sent to:', email);
    } catch (error) {
      console.error('Password reset error:', error);
      throw handleAuthError(error);
    }
  };

  // Handle Firebase auth errors
  const handleAuthError = (error) => {
    let message = 'An error occurred. Please try again.';
    
    switch (error.code) {
      case 'auth/email-already-in-use':
        message = 'This email is already registered. Please sign in instead.';
        break;
      case 'auth/invalid-email':
        message = 'Invalid email address.';
        break;
      case 'auth/operation-not-allowed':
        message = 'Email/password accounts are not enabled.';
        break;
      case 'auth/weak-password':
        message = 'Password is too weak. Please use at least 6 characters.';
        break;
      case 'auth/user-disabled':
        message = 'This account has been disabled.';
        break;
      case 'auth/user-not-found':
        message = 'No account found with this email.';
        break;
      case 'auth/wrong-password':
        message = 'Incorrect password.';
        break;
      case 'auth/invalid-credential':
        message = 'Invalid email or password.';
        break;
      case 'auth/too-many-requests':
        message = 'Too many failed attempts. Please try again later.';
        break;
      case 'auth/network-request-failed':
        message = 'Network error. Please check your connection.';
        break;
      default:
        message = error.message || 'Authentication failed.';
    }
    
    return new Error(message);
  };

  const value = {
    user,
    loading,
    initializing,
    signUp,
    signIn,
    logout,
    resetPassword
  };

  return (
    <AuthContext.Provider value={value}>
      {!initializing && children}
    </AuthContext.Provider>
  );
};

export default AuthContext;