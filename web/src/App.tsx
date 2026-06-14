import { useMemo } from "react";
import { PipecatClientProvider, PipecatClientAudio } from "@pipecat-ai/client-react";
import { createClient } from "./pcClient";
import PhoneFrame from "./components/PhoneFrame";

export default function App() {
  const client = useMemo(() => createClient(), []);

  return (
    // client-react's bundled .d.ts declares its own PipecatClient class, nominally
    // distinct from the one we construct though identical at runtime — cast here.
    <PipecatClientProvider client={client as never}>
      <PhoneFrame>
        <Splash />
      </PhoneFrame>
      {/* Plays Maya's TTS audio coming back from the bot. */}
      <PipecatClientAudio />
    </PipecatClientProvider>
  );
}

/** Phase 1 placeholder: brand mark only. Orb arrives in Phase 2. */
function Splash() {
  return (
    <div className="splash">
      <div className="brand-mark serif">Paytm Money</div>
      <div className="brand-tag">Wealth Expert</div>

      <style>{`
        .splash {
          height: 100%;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          gap: 8px;
          padding: 32px;
        }
        .brand-mark {
          font-size: 36px;
          line-height: 1;
          letter-spacing: -0.01em;
          color: var(--ivory);
          font-variation-settings: "opsz" 36, "wght" 400;
        }
        .brand-tag {
          font-size: 13px;
          letter-spacing: 0.22em;
          text-transform: uppercase;
          color: var(--champagne);
          font-weight: 500;
        }
      `}</style>
    </div>
  );
}
