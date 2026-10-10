import { runFeaturedStory, type FeaturedStory } from "../api/featured";
import { useChatStore } from "../stores/chatStore";
import { bboxCenterZoom, useMapStore } from "../stores/mapStore";
import { applyResultToGlobe } from "./applyResult";

let queued: FeaturedStory | null = null;

export function queueStory(story: FeaturedStory) {
  queued = story;
}

export function takeQueuedStory(): FeaturedStory | null {
  const story = queued;
  queued = null;
  return story;
}

export async function playStory(story: FeaturedStory) {
  const chat = useChatStore.getState();
  const stamp = Date.now();
  const { center, zoom } = bboxCenterZoom(story.bbox);
  useMapStore.getState().requestFlyTo(center, zoom);
  chat.addMessage({
    id: `story-q-${stamp}`,
    role: "user",
    text: `${story.title}, ${story.place} (${story.when})`,
  });
  const id = `story-${stamp}`;
  chat.addMessage({ id, role: "kairos", text: "Loading the radar result…", pending: true });
  try {
    const result = await runFeaturedStory(story.id);
    applyResultToGlobe(result);
    useChatStore.getState().updateMessage(id, { pending: false, text: story.summary, results: [result] });
  } catch (e) {
    useChatStore.getState().updateMessage(id, {
      pending: false,
      error: true,
      text: e instanceof Error ? e.message : "This story couldn't be loaded right now.",
    });
  }
}
