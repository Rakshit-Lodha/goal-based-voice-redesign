import { inr } from "../format";

/**
 * Cascade diff toast — surfaces when a revise loop knocks a downstream
 * number off its previous value (income → SIP, reprioritization → SIP).
 *
 * Renders as a transient pill near the bottom of the phone, slides in on
 * mount, and auto-dismisses after ~3.5s via the timeout in App.tsx.
 * Champagne accent on the new number so the change reads as a small
 * celebration / acknowledgement, not an error.
 */
export type CascadeDiff = {
  label: string;
  before: number;
  after: number;
};

export default function CascadeToast({ diff }: { diff: CascadeDiff }) {
  const arrow = diff.after >= diff.before ? "↑" : "↓";
  return (
    <div className="cascade-toast" role="status" aria-live="polite">
      <span className="cascade-label">{diff.label} updated</span>
      <span className="cascade-values">
        <span className="cascade-old">{inr(diff.before)}</span>
        <span className="cascade-arrow">{arrow}</span>
        <span className="cascade-new">{inr(diff.after)}</span>
      </span>
      <style>{`
        .cascade-toast {
          position: absolute;
          left: 50%;
          bottom: 132px;
          transform: translateX(-50%);
          z-index: 9;
          display: inline-flex;
          align-items: center;
          gap: 14px;
          padding: 12px 18px;
          background: rgba(10, 22, 40, 0.92);
          border: 1px solid rgba(201, 169, 97, 0.35);
          border-radius: 999px;
          color: var(--ivory);
          box-shadow: 0 12px 28px rgba(0, 0, 0, 0.35);
          backdrop-filter: blur(6px);
          animation: cascade-rise var(--dur-med, 360ms) var(--ease-out) both;
          white-space: nowrap;
          max-width: calc(100% - 32px);
        }
        .cascade-label {
          color: var(--ivory-soft);
          font-size: 11px;
          letter-spacing: 0.14em;
          text-transform: uppercase;
        }
        .cascade-values {
          display: inline-flex;
          align-items: baseline;
          gap: 8px;
          font-family: var(--font-display);
          font-weight: 400;
          font-size: 15px;
        }
        .cascade-old {
          color: var(--ivory-soft);
          text-decoration: line-through;
          opacity: 0.7;
        }
        .cascade-arrow { color: var(--champagne-soft); font-size: 13px; }
        .cascade-new { color: var(--champagne); font-size: 17px; }
        @keyframes cascade-rise {
          from { opacity: 0; transform: translate(-50%, 8px); }
          to   { opacity: 1; transform: translate(-50%, 0); }
        }
      `}</style>
    </div>
  );
}
