import { useEffect, useState } from "react";
import { usePipecatClientMediaTrack } from "@pipecat-ai/client-react";

/**
 * Tap-to-pause for Maya's audio.
 *
 * We mute the bot's MediaStreamTrack instead of disconnecting — the WebRTC
 * stream keeps flowing but the user hears silence. The backend keeps speaking
 * (frames continue to arrive); on resume, the user picks up audio at its
 * current position. Acceptable trade-off for Phase 3; a "true" pause that
 * halts TTS frame generation would need a backend RTVI message and is out
 * of scope here.
 */
export function usePause(): { isPaused: boolean; togglePause: () => void } {
  const [isPaused, setIsPaused] = useState(false);
  const botAudio = usePipecatClientMediaTrack("audio", "bot");

  useEffect(() => {
    if (botAudio) botAudio.enabled = !isPaused;
  }, [botAudio, isPaused]);

  return {
    isPaused,
    togglePause: () => setIsPaused((p) => !p),
  };
}
