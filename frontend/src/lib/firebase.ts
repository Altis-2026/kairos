import { initializeApp, type FirebaseApp } from "firebase/app";
import {
  getAuth,
  GoogleAuthProvider,
  signInWithPopup,
  signOut as fbSignOut,
  onAuthStateChanged,
  type Auth,
} from "firebase/auth";
import { getFirestore, type Firestore } from "firebase/firestore";
import { useAuthStore } from "../stores/authStore";

const apiKey = import.meta.env.VITE_FIREBASE_API_KEY as string | undefined;
const authDomain = import.meta.env.VITE_FIREBASE_AUTH_DOMAIN as string | undefined;
const projectId = import.meta.env.VITE_FIREBASE_PROJECT_ID as string | undefined;

export const firebaseEnabled = Boolean(apiKey && authDomain && projectId);

let app: FirebaseApp | null = null;
let auth: Auth | null = null;
let firestore: Firestore | null = null;

if (firebaseEnabled) {
  app = initializeApp({ apiKey, authDomain, projectId });
  auth = getAuth(app);
  firestore = getFirestore(app);
}

export const db = firestore;

export function initAuthListener() {
  const { setUser, setAuthReady } = useAuthStore.getState();
  if (!auth) {
    setAuthReady(true);
    return;
  }
  onAuthStateChanged(auth, (fbUser) => {
    setUser(
      fbUser
        ? {
            uid: fbUser.uid,
            name: fbUser.displayName,
            email: fbUser.email,
            photoUrl: fbUser.photoURL,
          }
        : null
    );
    setAuthReady(true);
  });
}

export async function signInWithGoogle(): Promise<void> {
  if (!auth) {
    throw new Error(
      "Sign-in is not configured yet. Add VITE_FIREBASE_API_KEY, " +
        "VITE_FIREBASE_AUTH_DOMAIN and VITE_FIREBASE_PROJECT_ID to frontend/.env."
    );
  }
  await signInWithPopup(auth, new GoogleAuthProvider());
}

export async function signOut(): Promise<void> {
  if (auth) await fbSignOut(auth);
}
