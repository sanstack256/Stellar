import { initializeApp } from "https://www.gstatic.com/firebasejs/10.13.0/firebase-app.js";
import {
  getAuth,
  GoogleAuthProvider,
  signInWithPopup,
  onAuthStateChanged,
  signOut
} from "https://www.gstatic.com/firebasejs/10.13.0/firebase-auth.js";

let authInstance = null;
let providerInstance = null;
let initPromise = null;

export async function getFirebaseAuth() {
  if (authInstance) return { auth: authInstance, provider: providerInstance };
  if (initPromise) return initPromise;

  initPromise = (async () => {
    try {
      const res = await fetch("/api/config/firebase");
      if (!res.ok) {
        throw new Error(`Failed to fetch Firebase configuration: ${res.status}`);
      }
      const config = await res.json();
      if (!config.apiKey) {
        throw new Error("Firebase API key is missing. Please configure FIREBASE_API_KEY in your .env file.");
      }
      const app = initializeApp(config);
      authInstance = getAuth(app);
      providerInstance = new GoogleAuthProvider();
      providerInstance.setCustomParameters({ prompt: "select_account" });
      return { auth: authInstance, provider: providerInstance };
    } catch (err) {
      initPromise = null;
      throw err;
    }
  })();

  return initPromise;
}

export async function signInWithGoogle() {
  const { auth, provider } = await getFirebaseAuth();
  const credential = await signInWithPopup(auth, provider);
  return credential.user;
}

export async function signOutUser() {
  const { auth } = await getFirebaseAuth();
  await signOut(auth);
}

export function onUserAuthStateChanged(callback) {
  getFirebaseAuth()
    .then(({ auth }) => {
      onAuthStateChanged(auth, callback);
    })
    .catch(() => {
      callback(null);
    });
}

export function getRedirectDestination() {
  const params = new URLSearchParams(window.location.search);
  const redirect = params.get("redirect");
  if (redirect && redirect.startsWith("/") && !redirect.startsWith("//")) {
    return redirect;
  }
  return "/";
}
