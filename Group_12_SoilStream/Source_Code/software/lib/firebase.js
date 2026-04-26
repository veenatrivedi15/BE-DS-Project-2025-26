// Mock Firebase configuration for development
// This allows the app to run without actual Firebase setup

class MockAuth {
  constructor() {
    this.currentUser = null;
    this.listeners = [];
  }

  async signInWithEmailAndPassword(email, password) {
    // Mock successful login
    const mockUser = {
      uid: 'mock-user-123',
      email: email,
      displayName: email.split('@')[0],
      toJSON: () => ({
        uid: 'mock-user-123',
        email: email,
        displayName: email.split('@')[0]
      })
    };
    this.currentUser = mockUser;
    this.listeners.forEach(listener => listener(mockUser));
    return { user: mockUser };
  }

  async createUserWithEmailAndPassword(email, password) {
    // Mock successful registration
    const mockUser = {
      uid: 'mock-user-' + Date.now(),
      email: email,
      displayName: email.split('@')[0],
      toJSON: () => ({
        uid: 'mock-user-' + Date.now(),
        email: email,
        displayName: email.split('@')[0]
      })
    };
    this.currentUser = mockUser;
    this.listeners.forEach(listener => listener(mockUser));
    return { user: mockUser };
  }

  async signOut() {
    this.currentUser = null;
    this.listeners.forEach(listener => listener(null));
  }

  onAuthStateChanged(callback) {
    this.listeners.push(callback);
    // Immediately call with current state
    callback(this.currentUser);
    
    // Return unsubscribe function
    return () => {
      this.listeners = this.listeners.filter(l => l !== callback);
    };
  }
}

class MockFirestore {
  constructor() {
    this.data = new Map();
  }

  collection(path) {
    return {
      doc: (id) => ({
        set: (data) => {
          this.data.set(`${path}/${id}`, data);
          return Promise.resolve();
        },
        get: () => {
          const data = this.data.get(`${path}/${id}`);
          return Promise.resolve({
            exists: !!data,
            data: () => data
          });
        },
        onSnapshot: (callback) => {
          const data = this.data.get(`${path}/${id}`);
          callback({
            exists: !!data,
            data: () => data
          });
          return () => {}; // unsubscribe
        }
      })
    };
  }
}

class MockStorage {
  ref(path) {
    return {
      put: (file) => {
        return Promise.resolve({
          ref: {
            getDownloadURL: () => Promise.resolve(`mock-url-${Date.now()}`)
          }
        });
      }
    };
  }
}

// Mock Firebase app
export const auth = new MockAuth();
export const firestore = new MockFirestore();
export const storage = new MockStorage();

// Mock Firebase functions
export const initializeApp = () => ({});
export const getAuth = () => auth;
export const getFirestore = () => firestore;
export const getStorage = () => storage;