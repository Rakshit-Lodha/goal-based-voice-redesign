import type { Mood } from "../state/useMood";

/**
 * The singleton orb. Centred inside the phone frame, mood-driven CSS.
 *
 * Pure CSS animation: a radial-gradient sphere plus a faint outer ring; both
 * pulse on different timings per mood. No animation library — conventions
 * call for CSS / Web Animations API only.
 *
 * Renders as a transparent <button> so tap-to-pause is keyboard-accessible.
 */
export default function Orb({
  mood,
  onTap,
  summoned = false,
  corner = false,
}: {
  mood: Mood;
  onTap?: () => void;
  summoned?: boolean;
  /** Plan-hero takeover: shrink the orb to the top-right corner with a
   *  champagne ring. Mutually exclusive with `summoned` — corner wins. */
  corner?: boolean;
}) {
  const cls = corner ? "is-corner" : summoned ? "is-summoned" : "";
  return (
    <button
      type="button"
      className={`orb-stage mood-${mood}${cls ? " " + cls : ""}`}
      onClick={onTap}
      aria-label={mood === "paused" ? "Resume Maya" : "Pause Maya"}
      aria-pressed={mood === "paused"}
    >
      <span className="orb-ring" />
      <span className="orb-core" />

      <style>{`
        .orb-stage {
          position: absolute;
          left: 50%;
          top: 50%;
          transform: translate(-50%, -50%);
          width: 240px;
          height: 240px;
          background: transparent;
          border: none;
          padding: 0;
          cursor: pointer;
          -webkit-tap-highlight-color: transparent;
          outline: none;
          transition: transform var(--dur-med) var(--ease-out);
        }
        .orb-stage.is-summoned {
          transform: translate(-50%, -50%) translateY(-160px) scale(0.55);
        }
        /* Plan-hero corner: orb anchors top-right, shrunk, with a thin
           champagne ring so it reads as "Maya is still here" while the
           plan cream takeover holds the screen. */
        .orb-stage.is-corner {
          left: auto;
          top: 28px;
          right: 28px;
          width: 56px;
          height: 56px;
          transform: none;
          z-index: 10;
        }
        .orb-stage.is-corner::before {
          content: "";
          position: absolute;
          inset: -7px;
          border-radius: 50%;
          border: 1px solid var(--champagne);
          opacity: 0.7;
          pointer-events: none;
        }
        .orb-stage:focus-visible {
          /* keyboard focus only — soft champagne ring around the orb area */
          box-shadow: 0 0 0 2px var(--champagne-soft);
          border-radius: 50%;
        }

        .orb-core,
        .orb-ring {
          position: absolute;
          inset: 0;
          border-radius: 50%;
          will-change: transform, opacity;
          pointer-events: none;
        }

        /* Inner luminous sphere — the heart of the orb. */
        .orb-core {
          background:
            radial-gradient(circle at 38% 32%,
              rgba(255, 255, 255, 0.85) 0%,
              var(--orb-tint, var(--orb-idle)) 38%,
              rgba(10, 22, 40, 0.0) 78%);
          filter: blur(0.2px);
        }

        /* Outer halo — slower, softer, gives the orb a "presence". */
        .orb-ring {
          background: radial-gradient(circle,
            var(--orb-tint, var(--orb-idle)) 0%,
            transparent 60%);
          opacity: 0.28;
          transform: scale(1.45);
        }

        /* ---- idle: slow breath, steel-blue. ---- */
        .mood-idle { --orb-tint: var(--orb-idle); }
        .mood-idle .orb-core {
          animation: orb-breath 4.2s var(--ease-in-out) infinite;
        }
        .mood-idle .orb-ring {
          animation: orb-halo 4.2s var(--ease-in-out) infinite;
        }

        /* ---- listening: brighter blue, faster pulse. ---- */
        .mood-listening { --orb-tint: var(--orb-listening); }
        .mood-listening .orb-core {
          animation: orb-pulse 1.6s var(--ease-in-out) infinite;
        }
        .mood-listening .orb-ring {
          animation: orb-halo 1.6s var(--ease-in-out) infinite;
          opacity: 0.38;
        }

        /* ---- talking: champagne, gentle measured pulse. ---- */
        .mood-talking { --orb-tint: var(--orb-talking); }
        .mood-talking .orb-core {
          animation: orb-talk 2.4s var(--ease-in-out) infinite;
        }
        .mood-talking .orb-ring {
          animation: orb-halo 2.4s var(--ease-in-out) infinite;
          opacity: 0.42;
        }

        /* ---- paused: dim, frozen. ---- */
        .mood-paused { --orb-tint: var(--orb-paused); }
        .mood-paused .orb-core,
        .mood-paused .orb-ring {
          animation: none;
          opacity: 0.4;
        }

        @keyframes orb-breath {
          0%, 100% { transform: scale(1.00); opacity: 0.90; }
          50%      { transform: scale(1.04); opacity: 1.00; }
        }
        @keyframes orb-pulse {
          0%, 100% { transform: scale(1.00); opacity: 0.95; }
          50%      { transform: scale(1.08); opacity: 1.00; }
        }
        @keyframes orb-talk {
          0%, 100% { transform: scale(1.00); opacity: 0.95; }
          50%      { transform: scale(1.035); opacity: 1.00; }
        }
        @keyframes orb-halo {
          0%, 100% { transform: scale(1.40); }
          50%      { transform: scale(1.55); }
        }

        @media (prefers-reduced-motion: reduce) {
          .orb-core, .orb-ring { animation: none !important; }
        }
      `}</style>
    </button>
  );
}
