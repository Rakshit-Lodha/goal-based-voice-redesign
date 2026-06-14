import { useState } from "react";
import { useRtviEvent } from "../pcReact";

/**
 * The orb's mood — what Maya is doing right now.
 *  - idle: silence, breathing
 *  - listening: the user is speaking; Maya is taking it in
 *  - talking: Maya is speaking
 *  - paused: tap-to-pause (Phase 3)
 */
export type Mood = "idle" | "listening" | "talking" | "paused";

/**
 * Subscribes to Pipecat speaking events and derives a single mood. Bot
 * speaking wins over user speaking — if both flags overlap on a barge-in,
 * we surface "talking" until BotStoppedSpeaking, matching the audio truth.
 */
export function useMood(): Mood {
  const [botSpeaking, setBotSpeaking] = useState(false);
  const [userSpeaking, setUserSpeaking] = useState(false);

  useRtviEvent("botStartedSpeaking", () => setBotSpeaking(true));
  useRtviEvent("botStoppedSpeaking", () => setBotSpeaking(false));
  useRtviEvent("userStartedSpeaking", () => setUserSpeaking(true));
  useRtviEvent("userStoppedSpeaking", () => setUserSpeaking(false));

  if (botSpeaking) return "talking";
  if (userSpeaking) return "listening";
  return "idle";
}
