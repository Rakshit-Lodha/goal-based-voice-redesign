/**
 * Top bar inside the phone frame.
 *
 * Left: "Paytm Money" wordmark in Fraunces.
 * Right: ledger chip placeholder — Phase 7 wires the live STATE count.
 *        Disabled in Phase 3 so the visual is right but the surface inert.
 */
export default function BrandBar() {
  return (
    <header className="brand-bar">
      <div className="wordmark serif">Paytm Money</div>
      <button
        type="button"
        className="ledger-chip"
        disabled
        aria-label="Ledger (available once Maya confirms a fact)"
      >
        <span className="dot" />
        <span>Ledger</span>
      </button>

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
          color: var(--ivory);
          letter-spacing: 0.005em;
          font-variation-settings: "opsz" 18, "wght" 400;
        }
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
                      border-color var(--dur-fast) var(--ease-out);
        }
        .ledger-chip .dot {
          width: 6px;
          height: 6px;
          border-radius: 50%;
          background: var(--ivory-soft);
        }
      `}</style>
    </header>
  );
}
