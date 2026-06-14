import { useMemo } from "react";
import { PipecatClientProvider, PipecatClientAudio } from "@pipecat-ai/client-react";
import { createClient } from "./pcClient";
import PhoneFrame from "./components/PhoneFrame";
import Orb from "./components/Orb";
import { useMood } from "./state/useMood";

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
 * Phase 2: just the centred orb, mood-driven.
 * Phase 3 will add subtitle, mic affordance, brand bar around it.
 */
function Conversation() {
  const mood = useMood();
  return <Orb mood={mood} />;
}
