import LedgerChip from "./LedgerChip";

/**
 * Top bar inside the phone frame.
 *
 * Left: "ABCD" wordmark in Fraunces gold.
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
      <div className="wordmark serif">ABCD</div>
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
          font-size: 17px;
          line-height: 1;
          color: var(--champagne);
          letter-spacing: 0.02em;
          font-variation-settings: "opsz" 18, "wght" 500;
        }
      `}</style>
    </header>
  );
}
