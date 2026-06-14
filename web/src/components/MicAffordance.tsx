type MicState = "idle" | "connecting" | "live";

/**
 * Bottom-centre voice affordance. Before the call is live, this is the one
 * explicit browser gesture that starts WebRTC and triggers mic permission.
 * Once connected, it becomes quiet status text.
 */
export default function MicAffordance({
  state,
  onStart,
  onEnd,
  error,
}: {
  state: MicState;
  onStart: () => void;
  onEnd: () => void;
  error?: string | null;
}) {
  const live = state === "live";
  const connecting = state === "connecting";

  return (
    <button
      type="button"
      className={`mic mic-${state}`}
      onClick={live ? onEnd : onStart}
      disabled={connecting}
      aria-label={live ? "End call with Maya" : "Start call with Maya"}
    >
      <svg
        className="mic-icon"
        viewBox="0 0 24 24"
        width="22"
        height="22"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <rect x="9" y="3" width="6" height="12" rx="3" />
        <path d="M5 11a7 7 0 0 0 14 0" />
        <path d="M12 18v3" />
      </svg>
      <div className="mic-label">
        {live ? "Live · tap to end" : connecting ? "Connecting..." : "Tap to start"}
      </div>
      {error && <div className="mic-error">{error}</div>}

      <style>{`
        .mic {
          position: absolute;
          left: 50%;
          bottom: 56px;
          transform: translateX(-50%);
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 8px;
          color: var(--ivory-soft);
          -webkit-tap-highlight-color: transparent;
        }
        .mic:not(:disabled):hover .mic-icon {
          color: var(--champagne-soft);
          opacity: 1;
        }
        .mic:disabled {
          cursor: progress;
          opacity: 0.72;
        }
        .mic-icon { opacity: 0.7; transition: color var(--dur-fast) var(--ease-out), opacity var(--dur-fast) var(--ease-out); }
        .mic-live .mic-icon { color: var(--green-soft); opacity: 1; }
        .mic-label {
          font-size: 12px;
          font-weight: 500;
          letter-spacing: 0.06em;
          text-transform: uppercase;
          color: var(--ivory-soft);
        }
        .mic-error {
          max-width: 260px;
          color: var(--champagne-soft);
          font-size: 11px;
          line-height: 1.35;
          text-align: center;
        }
      `}</style>
    </button>
  );
}
