import type { LedgerRow } from "../state/ledgerRows";

/**
 * The ledger panel — slides down from the top of the phone frame and
 * lists every Maya-confirmed fact. Each row carries a Revise CTA whose
 * onRevise(reviseKey) is wired in Phase 8 to send a synthetic user
 * message back to the bot ("I want to update my <key>").
 *
 * Tap-only entry/exit (open question #4 resolution). The full-panel
 * scrim catches taps outside the visible card to close.
 */
export default function LedgerPanel({
  rows,
  isOpen,
  onClose,
  onRevise,
}: {
  rows: LedgerRow[];
  isOpen: boolean;
  onClose: () => void;
  onRevise: (key: string) => void;
}) {
  if (!isOpen) return null;

  return (
    <div className="ledger-scrim" onClick={onClose} role="dialog" aria-modal="true" aria-label="Ledger">
      <section className="ledger-panel" onClick={(event) => event.stopPropagation()}>
        <header className="ledger-head">
          <div>
            <div className="ledger-eyebrow">Confirmed</div>
            <h2 className="serif">Ledger</h2>
          </div>
          <button type="button" className="ledger-close" onClick={onClose} aria-label="Close ledger">×</button>
        </header>

        {rows.length === 0 ? (
          <p className="ledger-empty">Nothing confirmed yet. Maya's first fact will appear here.</p>
        ) : (
          <ul className="ledger-rows">
            {rows.map((row) => (
              <li key={row.id}>
                <div className="ledger-row-text">
                  <div className="ledger-row-title">{row.title}</div>
                  <div className="ledger-row-value">{row.value}</div>
                </div>
                <button
                  type="button"
                  className="ledger-revise"
                  onClick={() => onRevise(row.reviseKey)}
                >
                  Revise
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <style>{`
        .ledger-scrim {
          position: absolute;
          inset: 0;
          z-index: 7;
          background: rgba(10, 22, 40, 0.55);
          backdrop-filter: blur(2px);
          animation: scrim-fade var(--dur-med) var(--ease-out) both;
        }
        .ledger-panel {
          position: absolute;
          left: 0;
          right: 0;
          top: 0;
          max-height: 78%;
          overflow: auto;
          padding: 24px 22px 28px;
          border-bottom-left-radius: 24px;
          border-bottom-right-radius: 24px;
          background: var(--navy-soft);
          color: var(--ivory);
          box-shadow: 0 24px 60px rgba(0, 0, 0, 0.45);
          animation: panel-drop var(--dur-med) var(--ease-out) both;
        }
        .ledger-head {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          padding-top: 32px;
        }
        .ledger-eyebrow {
          color: var(--ivory-soft);
          font-size: 11px;
          letter-spacing: 0.18em;
          text-transform: uppercase;
        }
        .ledger-head h2 {
          margin: 4px 0 0;
          font-size: 26px;
          line-height: 1;
          color: var(--ivory);
          font-variation-settings: "opsz" 36, "wght" 400;
        }
        .ledger-close {
          width: 32px;
          height: 32px;
          border-radius: 50%;
          color: var(--ivory-soft);
          font-size: 22px;
          line-height: 1;
        }
        .ledger-close:hover { color: var(--ivory); }
        .ledger-empty {
          margin: 20px 0 0;
          color: var(--ivory-soft);
          font-size: 14px;
          font-style: italic;
          font-family: var(--font-display);
        }
        .ledger-rows {
          margin: 22px 0 0;
          padding: 0;
          list-style: none;
          display: grid;
          gap: 0;
        }
        .ledger-rows li {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 14px;
          padding: 14px 0;
          border-bottom: 1px solid var(--ivory-hairline);
        }
        .ledger-rows li:last-child { border-bottom: none; }
        .ledger-row-text { min-width: 0; }
        .ledger-row-title {
          color: var(--ivory);
          font-family: var(--font-display);
          font-variation-settings: "opsz" 24, "wght" 400;
          font-size: 16px;
          line-height: 1.2;
        }
        .ledger-row-value {
          margin-top: 4px;
          color: var(--ivory-soft);
          font-size: 13px;
          line-height: 1.3;
          word-break: break-word;
        }
        .ledger-revise {
          flex: none;
          padding: 6px 12px;
          border-radius: 999px;
          border: 1px solid var(--ivory-hairline);
          color: var(--champagne-soft);
          font-size: 11px;
          font-weight: 500;
          letter-spacing: 0.12em;
          text-transform: uppercase;
          transition: border-color var(--dur-fast) var(--ease-out),
                      color var(--dur-fast) var(--ease-out);
        }
        .ledger-revise:hover {
          border-color: var(--champagne);
          color: var(--champagne);
        }
        @keyframes panel-drop {
          from { transform: translateY(-12%); opacity: 0; }
          to   { transform: translateY(0); opacity: 1; }
        }
        @keyframes scrim-fade {
          from { opacity: 0; }
          to   { opacity: 1; }
        }
      `}</style>
    </div>
  );
}
