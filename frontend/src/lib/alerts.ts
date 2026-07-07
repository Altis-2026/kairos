import {
  addDoc,
  collection,
  deleteDoc,
  doc,
  getDocs,
  query,
  updateDoc,
  where,
} from "firebase/firestore";
import { db } from "./firebase";
import { useAuthStore } from "../stores/authStore";
import { useAlertsStore, type SavedAlert } from "../stores/alertsStore";
import type { ResultRef } from "../types/map";

const COLLECTION = "alerts";

export const alertsAvailable = () => Boolean(db);

export async function createAlert(ref: ResultRef): Promise<void> {
  const user = useAuthStore.getState().user;
  if (!db || !user) return;
  const payload = {
    userId: user.uid,
    label: ref.displayName,
    analysisType: ref.analysisType,
    displayName: ref.displayName,
    bbox: ref.bbox,
    lastDataDate: ref.dataDate || null,
    lastHeadlineValue: ref.headlineValue ?? null,
    lastHeadlineUnit: ref.headlineUnit ?? null,
    lastCheckedAt: Date.now(),
    createdAt: Date.now(),
  };
  try {
    const docRef = await addDoc(collection(db, COLLECTION), payload);
    useAlertsStore.getState().addAlert({ id: docRef.id, ...payload });
  } catch (e) {
    console.warn("[kairos] createAlert skipped:", e);
    throw e;
  }
}

export async function loadAlerts(): Promise<void> {
  const user = useAuthStore.getState().user;
  const store = useAlertsStore.getState();
  if (!db || !user) {
    store.setAlerts([]);
    return;
  }
  store.setLoading(true);
  store.setError(null);
  try {
    const q = query(collection(db, COLLECTION), where("userId", "==", user.uid));
    const snap = await getDocs(q);
    const alerts = snap.docs
      .map((d) => ({ id: d.id, ...(d.data() as Omit<SavedAlert, "id">) }))
      .sort((a, b) => b.createdAt - a.createdAt);
    store.setAlerts(alerts);
  } catch (e) {
    store.setError(
      e instanceof Error ? e.message : "Could not load alerts. Is Firestore enabled?"
    );
  } finally {
    store.setLoading(false);
  }
}

export async function markAlertChecked(
  id: string,
  patch: { lastDataDate?: string; lastHeadlineValue?: number; lastHeadlineUnit?: string }
): Promise<void> {
  const update = { ...patch, lastCheckedAt: Date.now() };
  useAlertsStore.getState().updateAlert(id, update);
  if (!db) return;
  try {
    await updateDoc(doc(db, COLLECTION, id), update);
  } catch (e) {
    console.warn("[kairos] markAlertChecked failed:", e);
  }
}

export async function deleteAlert(id: string): Promise<void> {
  useAlertsStore.getState().removeAlert(id);
  if (!db) return;
  try {
    await deleteDoc(doc(db, COLLECTION, id));
  } catch (e) {
    console.warn("[kairos] deleteAlert failed:", e);
  }
}
