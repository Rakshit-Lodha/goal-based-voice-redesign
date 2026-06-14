import { useMemo } from "react";
import { PipecatClientProvider, PipecatClientAudio } from "@pipecat-ai/client-react";
import { createClient } from "./pcClient";
import PhoneFrame from "./components/PhoneFrame";
import BrandBar from "./components/BrandBar";
import Orb from "./components/Orb";
import Subtitle from "./components/Subtitle";
import MicAffordance from "./components/MicAffordance";
import { useMood, type Mood } from "./state/useMood";
import { usePause } from "./state/usePause";

export default function App() {
  const client = useMemo(() => createClient(), []);

  return (
    // client-react's bundled .d.ts declares its own PipecatClient class, nominally
    // distinct from the one we construct though identical at runtime — cast here.
    <PipecatClientProvider client={client as never}>
      <PhoneFrame>
        <Conversation />
      </PhoneFrame>
      {/* Plays Maya's TTS audio coming back from the bot. */}
      <PipecatClientAudio />
    </PipecatClientProvider>
  );
}

/**
 * The conversation shell: brand bar (top), orb (centre, tap-to-pause),
 * subtitle (just below orb), mic affordance (bottom).
 *
 * Phase 4–7 will surface artifacts above the mic affordance and replace
 * the ledger chip placeholder with the live STATE-driven version.
 */
function Conversation() {
  const baseMood = useMood();
  const { isPaused, togglePause } = usePause();
  const mood: Mood = isPaused ? "paused" : baseMood;

  return (
    <>
      <BrandBar />
      <Orb mood={mood} onTap={togglePause} />
      <Subtitle mood={mood} />
      <MicAffordance />
    </>
  );
}
