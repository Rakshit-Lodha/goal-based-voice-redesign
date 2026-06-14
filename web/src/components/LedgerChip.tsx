/**
 * The ledger chip in the top-right of the brand bar.
 *
 * `count === 0` renders the pre-conversation placeholder (faint hairline,
 * cursor not-allowed) so the surface is visually present but inert until
 * Maya confirms her first fact. Once anything is confirmed, the chip
 * gains its champagne ring and becomes the entry point to the ledger.
 *
 * Open question #4 resolved Phase 7: tap-only. Voice-first means hands
 * are free; swipe-down across screen would conflict with orb tap-to-pause.
 */
export default function LedgerChip({
  count,
  onClick,
}: {
  count: number;
  onClick?: () => void;
}) {
  const live = count > 0;
  return (
    <button
      type="button"
      className={`ledger-chip${live ? " is-live" : ""}`}
      onClick={live ? onClick : undefined}
      disabled={!live}
      aria-label={live ? `Open ledger · ${count} confirmed fact${count === 1 ? "" : "s"}` : "Ledger (no confirmed facts yet)"}
    >
      <span className="dot" />
      <span className="label">Ledger</span>
      {live && <span className="count">{count}</span>}

      <style>{`
        .ledger-chip {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          padding: 6px 12px;
          border-radius: 999px;
          border: 1px solid var(--ivory-hairline);
          background: rgba(245, 237, 219, 0.03);
          color: var(--ivory-soft);
          font-family: inherit;
          font-size: 12px;
          font-weight: 500;
          letter-spacing: 0.06em;
          text-transform: uppercase;
          opacity: 0.6;
          cursor: not-allowed;
          transition: opacity var(--dur-fast) var(--ease-out),
                      border-color var(--dur-fast) var(--ease-out),
                      color var(--dur-fast) var(--ease-out);
        }
        .ledger-chip.is-live {
          opacity: 1;
          cursor: pointer;
          border-color: rgba(201, 169, 97, 0.45);
          color: var(--ivory);
          background: rgba(201, 169, 97, 0.06);
        }
        .ledger-chip.is-live:hover { border-color: var(--champagne); }
        .ledger-chip .dot {
          width: 6px;
          height: 6px;
          border-radius: 50%;
          background: var(--ivory-soft);
        }
        .ledger-chip.is-live .dot { background: var(--champagne); }
        .ledger-chip .count {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          min-width: 18px;
          height: 18px;
          padding: 0 5px;
          margin-left: 2px;
          border-radius: 999px;
          background: var(--champagne);
          color: var(--navy);
          font-family: var(--font-display);
          font-size: 11px;
          font-weight: 500;
          letter-spacing: 0;
        }
      `}</style>
    </button>
  );
}
