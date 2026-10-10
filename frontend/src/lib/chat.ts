import { runQuery } from "../api/query";
import { isCancelled } from "../api/client";
import { useChatStore } from "../stores/chatStore";
import { useMapStore } from "../stores/mapStore";
import { usePrefsStore } from "../stores/prefsStore";
import { applyResultToGlobe } from "./applyResult";
import { speak } from "./voice";
import { speechLang, translate, type StringKey } from "./i18n";

let msgId = 0;
const nextId = () => `m${++msgId}-${Date.now()}`;

let active: AbortController | null = null;
let stageTimer: ReturnType<typeof setInterval> | null = null;

const STAGES: StringKey[] = ["stage1", "stage2", "stage3", "stage4"];
const STAGE_AT_MS = [0, 3500, 9000, 30000];

function t(key: StringKey) {
  return translate(usePrefsStore.getState().locale, key);
}

export function stopAsking() {
  active?.abort("user");
}

export async function ask(text: string) {
  const query = text.trim();
  const chat = useChatStore.getState();
  if (!query || chat.loading) return;

  const history = chat.messages
    .filter((m) => !m.pending && !m.error)
    .slice(-8)
    .map((m) => ({ role: m.role, content: m.text }));

  chat.addMessage({ id: nextId(), role: "user", text: query });
  const pendingId = nextId();
  chat.addMessage({ id: pendingId, role: "kairos", text: `${t("stage1")}…`, pending: true });
  chat.setLoading(true);

  const started = Date.now();
  stageTimer = setInterval(() => {
    const elapsed = Date.now() - started;
    let stage = 0;
    STAGE_AT_MS.forEach((at, i) => {
      if (elapsed >= at) stage = i;
    });
    useChatStore.getState().updateMessage(pendingId, { text: `${t(STAGES[stage])}…` });
  }, 500);

  active = new AbortController();
  const update = (patch: Parameters<typeof chat.updateMessage>[1]) =>
    useChatStore.getState().updateMessage(pendingId, { pending: false, ...patch });

  try {
    const locale = usePrefsStore.getState().locale;
    const res = await runQuery(query, useMapStore.getState().viewportBbox ?? undefined, history, {
      signal: active.signal,
      language: locale === "es" ? "es" : navigator.language,
    });

    if (!res.understood) {
      update({ text: res.clarification ?? t("clarify") });
      return;
    }

    const all = res.results?.length ? res.results : res.result ? [res.result] : [];
    for (const r of all.slice(1).reverse()) applyResultToGlobe(r);
    if (all[0]) applyResultToGlobe(all[0]);

    const params = res.parameters as Record<string, unknown> | null;
    const reasoning = typeof params?.reasoning === "string" ? params.reasoning : undefined;
    const reply = res.explanation ?? t("done");
    update({ text: reply, reasoning, results: all });
    if (usePrefsStore.getState().speakReplies) speak(reply, speechLang(locale));
  } catch (e) {
    if (isCancelled(e)) update({ text: t("cancelled") });
    else update({ text: e instanceof Error ? e.message : String(e), error: true });
  } finally {
    if (stageTimer) clearInterval(stageTimer);
    stageTimer = null;
    active = null;
    useChatStore.getState().setLoading(false);
  }
}
