import LedgerChip from "./LedgerChip";

/**
 * Top bar inside the phone frame.
 *
 * Left: neutral Northstar wordmark.
 * Right: live LedgerChip — count of facts Maya has confirmed.
 *        Pre-conversation (count 0) it renders the dim placeholder;
 *        once anything is confirmed it activates and opens the panel.
 */
export default function BrandBar({
  ledgerCount,
  onLedgerOpen,
}: {
  ledgerCount: number;
  onLedgerOpen: () => void;
}) {
  return (
    <header className="brand-bar">
      <div className="wordmark">
        <span className="wordmark-symbol">N</span>
        <span>Northstar</span>
      </div>
      <LedgerChip count={ledgerCount} onClick={onLedgerOpen} />

      <style>{`
        .brand-bar {
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          height: 64px;
          padding: 0 20px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          z-index: 2;
          pointer-events: auto;
        }
        .wordmark {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 14px;
          font-weight: 650;
          line-height: 1;
          color: var(--ivory);
          letter-spacing: 0.01em;
        }
        .wordmark-symbol {
          width: 27px;
          height: 27px;
          display: grid;
          place-items: center;
          border-radius: 9px 9px 9px 3px;
          color: var(--navy);
          background: var(--champagne);
          font-family: var(--font-display);
          font-size: 16px;
        }
      `}</style>
    </header>
  );
}
