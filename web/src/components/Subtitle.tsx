import type { Mood } from "../state/useMood";

/**
 * Single italic Fraunces line below the orb that names what's happening.
 * Idle is intentionally blank — the orb's breath is the only "ambient" cue;
 * we don't add UI to say "nothing is happening".
 */
const COPY: Record<Mood, string> = {
  idle: "",
  listening: "Maya is listening",
  talking: "Maya is speaking",
  paused: "Paused · tap orb to resume",
};

export default function Subtitle({ mood }: { mood: Mood }) {
  const text = COPY[mood];
  return (
    <div className="subtitle serif italic" aria-live="polite">
      <span className={text ? "visible" : ""}>{text || " "}</span>

      <style>{`
        .subtitle {
          position: absolute;
          left: 0;
          right: 0;
          top: 50%;
          margin-top: 152px; /* 120 (orb radius) + 32 breathing room */
          text-align: center;
          font-size: 17px;
          color: var(--ivory-soft);
          letter-spacing: 0.005em;
          pointer-events: none;
        }
        .subtitle > span {
          display: inline-block;
          opacity: 0;
          transition: opacity var(--dur-med) var(--ease-out);
          font-variation-settings: "opsz" 24, "wght" 400;
        }
        .subtitle > span.visible {
          opacity: 1;
        }
      `}</style>
    </div>
  );
}
