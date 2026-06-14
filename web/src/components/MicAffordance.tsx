/**
 * Bottom-centre voice affordance. Purely informational — the mic is always
 * hot via Pipecat's enableMic on the client; this just signals "you can speak".
 * Tap-to-pause lives on the orb itself; this isn't a button.
 */
export default function MicAffordance() {
  return (
    <div className="mic" aria-hidden="true">
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
      <div className="mic-label">Tap or just talk</div>

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
        }
        .mic-icon { opacity: 0.7; }
        .mic-label {
          font-size: 12px;
          font-weight: 500;
          letter-spacing: 0.06em;
          text-transform: uppercase;
          color: var(--ivory-soft);
        }
      `}</style>
    </div>
  );
}
