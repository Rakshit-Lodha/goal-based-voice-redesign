import type { ArtifactEvent } from "../types";
import { renderArtifact } from "../state/artifactRegistry";

export default function Artifact({
  artifact,
  onDismiss,
}: {
  artifact: ArtifactEvent | null;
  onDismiss: () => void;
}) {
  if (!artifact) return null;

  return (
    <aside className="artifact-sheet" aria-live="polite">
      <button type="button" className="artifact-close" onClick={onDismiss} aria-label="Dismiss artifact">
        ×
      </button>
      {renderArtifact(artifact)}

      <style>{`
        .artifact-sheet {
          position: absolute;
          left: 16px;
          right: 16px;
          bottom: 16px;
          z-index: 6;
          max-height: min(64%, 540px);
          overflow: auto;
          padding: 26px;
          border-radius: 28px;
          background: var(--cream);
          color: var(--ink);
          box-shadow:
            0 24px 70px rgba(0, 0, 0, 0.28),
            0 0 0 1px rgba(26, 31, 46, 0.06);
          animation: artifact-rise var(--dur-med) var(--ease-out) both;
        }
        .artifact-close {
          position: absolute;
          top: 16px;
          right: 16px;
          width: 32px;
          height: 32px;
          border-radius: 50%;
          color: var(--ink-soft);
          font-size: 22px;
          line-height: 1;
        }
        .artifact-card-eyebrow {
          margin-bottom: 10px;
          color: var(--ink-soft);
          font-size: 11px;
          letter-spacing: 0.16em;
          text-transform: uppercase;
        }
        .artifact-card-title {
          margin: 0;
          max-width: 280px;
          color: var(--ink);
          font-family: var(--font-display);
          font-size: 28px;
          font-weight: 400;
          line-height: 1.12;
        }
        .artifact-card-title.xl { font-size: 38px; }
        .artifact-card-lede {
          margin: 12px 0 0;
          color: var(--ink-soft);
          font-size: 14px;
          line-height: 1.5;
        }
        .artifact-metrics {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 10px;
          margin-top: 18px;
        }
        .artifact-metric {
          min-width: 0;
          padding: 12px;
          border: 1px solid var(--cream-deep);
          border-radius: 14px;
          background: rgba(255, 255, 255, 0.26);
        }
        .artifact-metric span {
          display: block;
          color: var(--ink-soft);
          font-size: 10px;
          letter-spacing: 0.12em;
          text-transform: uppercase;
        }
        .artifact-metric b {
          display: block;
          margin-top: 6px;
          color: var(--ink);
          font-family: var(--font-display);
          font-size: 20px;
          font-weight: 400;
          line-height: 1.1;
        }
        .artifact-list {
          margin: 16px 0 0;
          padding: 0;
          list-style: none;
          display: grid;
          gap: 10px;
        }
        .artifact-list li {
          display: flex;
          justify-content: space-between;
          gap: 14px;
          padding-bottom: 10px;
          border-bottom: 1px solid var(--cream-deep);
          color: var(--ink-soft);
          font-size: 13px;
          line-height: 1.35;
        }
        .artifact-list li:last-child {
          border-bottom: none;
          padding-bottom: 0;
        }
        .artifact-list b {
          color: var(--ink);
          font-weight: 500;
          text-align: right;
        }
        .artifact-curve {
          width: 100%;
          height: 108px;
          margin-top: 12px;
        }
        @keyframes artifact-rise {
          from { transform: translateY(120%); }
          to { transform: translateY(0); }
        }
      `}</style>
    </aside>
  );
}
