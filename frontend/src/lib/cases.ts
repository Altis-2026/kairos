/**
 * Saved analyses ("cases") persisted per signed-in user in Firestore.
 *
 * Everything degrades gracefully: with no Firebase config, no signed-in user,
 * or Firestore not yet enabled in the console, these become safe no-ops so the
 * app never breaks — saving is a bonus for signed-in users, not a requirement.
 */
import {
  addDoc,
  collection,
  deleteDoc,
  doc,
  getDocs,
  query,
  where,
} from "firebase/firestore";
import { db } from "./firebase";
import { useAuthStore } from "../stores/authStore";
import { useCasesStore, type SavedCase } from "../stores/casesStore";
import type { AnalysisResult } from "../types/analysis";

const COLLECTION = "cases";

/** Whether persistence is wired (Firebase configured). */
export const casesAvailable = () => Boolean(db);

/** Fire-and-forget save of a finished analysis for the current user. */
export async function saveCase(result: AnalysisResult): Promise<void> {
  const user = useAuthStore.getState().user;
  if (!db || !user) return;
  const payload = {
    userId: user.uid,
    analysisType: result.analysis_type,
    displayName: result.display_name,
    bbox: result.bbox,
    startDate: result.start_date,
    endDate: result.end_date,
    dataDate: result.data_date,
    headlineLabel: result.headline_stat.label,
    headlineValue: result.headline_stat.value,
    headlineUnit: result.headline_stat.unit,
    createdAt: Date.now(),
  };
  try {
    const ref = await addDoc(collection(db, COLLECTION), payload);
    useCasesStore.getState().addCase({ id: ref.id, ...payload });
  } catch (e) {
    // Firestore not enabled / rules / offline — non-fatal.
    console.warn("[kairos] saveCase skipped:", e);
  }
}

/** Load the signed-in user's saved cases into the store (newest first). */
export async function loadCases(): Promise<void> {
  const user = useAuthStore.getState().user;
  const store = useCasesStore.getState();
  if (!db || !user) {
    store.setCases([]);
    return;
  }
  store.setLoading(true);
  store.setError(null);
  try {
    // Query by user only and sort client-side — avoids a composite index.
    const q = query(collection(db, COLLECTION), where("userId", "==", user.uid));
    const snap = await getDocs(q);
    const cases = snap.docs
      .map((d) => ({ id: d.id, ...(d.data() as Omit<SavedCase, "id">) }))
      .sort((a, b) => b.createdAt - a.createdAt);
    store.setCases(cases);
  } catch (e) {
    store.setError(
      e instanceof Error
        ? e.message
        : "Could not load saved analyses. Is Firestore enabled?"
    );
  } finally {
    store.setLoading(false);
  }
}

export async function deleteCase(id: string): Promise<void> {
  if (!db) return;
  try {
    await deleteDoc(doc(db, COLLECTION, id));
    useCasesStore.getState().removeCase(id);
  } catch (e) {
    console.warn("[kairos] deleteCase failed:", e);
  }
}
