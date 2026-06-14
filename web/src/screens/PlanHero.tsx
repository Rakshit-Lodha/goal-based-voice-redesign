/**
 * Plan reveal — the moment.
 *
 * When the `plan_hero` artifact arrives (emitted by generate_plan_pdf at
 * the very end of the session), the orb shrinks to a champagne-ringed
 * corner and the cream surface takes the screen. The 84px Fraunces SIP
 * number is the single visual centrepiece — no other UI competes with it.
 *
 * Pure cream takeover so the user reads it as "the plan", not as a card.
 * Bypasses the bottom-sheet Artifact wrapper — the special case lives in
 * App.tsx, not in artifactRegistry, so this screen owns its own layout.
 */
export default function PlanHero({
  data,
  onDismiss,
}: {
  data: {
    total_monthly_sip?: number;
    fund_count?: number;
    funds?: Array<{ name: string; monthly_sip?: number }>;
    pdf_url?: string;
  };
  onDismiss: () => void;
}) {
  const sip = data.total_monthly_sip ?? 0;
  const funds = Array.isArray(data.funds) ? data.funds : [];
  const fundCount = data.fund_count ?? funds.length;

  return (
    <section className="plan-hero" aria-live="polite">
      <div className="plan-hero-inner">
        <div className="eyebrow">Your monthly SIP</div>
        <div className="amount serif">{formatRupees(sip)}</div>
        {fundCount > 0 && (
          <div className="across">across {fundCount} {fundCount === 1 ? "fund" : "funds"}</div>
        )}

        {funds.length > 0 && (
          <ul className="funds">
            {funds.slice(0, 6).map((fund, i) => (
              <li key={i}>
                <span>{fund.name}</span>
                {typeof fund.monthly_sip === "number" && (
                  <b>{formatRupees(fund.monthly_sip)}</b>
                )}
              </li>
            ))}
          </ul>
        )}

        <div className="actions">
          {data.pdf_url && (
            <a className="ghost" href={data.pdf_url} target="_blank" rel="noreferrer">
              Open plan PDF
            </a>
          )}
          <button type="button" className="primary" onClick={onDismiss}>
            Looks good
          </button>
        </div>
      </div>

      <style>{`
        .plan-hero {
          position: absolute;
          inset: 0;
          z-index: 8;
          background: var(--cream);
          color: var(--ink);
          padding: 96px 28px 32px;
          overflow: auto;
          animation: hero-rise var(--dur-slow) var(--ease-out) both;
        }
        .plan-hero-inner {
          display: flex;
          flex-direction: column;
          gap: 18px;
        }
        .eyebrow {
          color: var(--ink-soft);
          font-size: 11px;
          letter-spacing: 0.22em;
          text-transform: uppercase;
        }
        .amount {
          margin: 0;
          font-size: 84px;
          line-height: 0.92;
          letter-spacing: -0.02em;
          color: var(--ink);
          font-variation-settings: "opsz" 144, "wght" 400;
        }
        .across {
          color: var(--ink-soft);
          font-size: 14px;
          letter-spacing: 0.02em;
        }
        .funds {
          margin: 20px 0 0;
          padding: 0;
          list-style: none;
          display: grid;
          gap: 12px;
        }
        .funds li {
          display: flex;
          justify-content: space-between;
          gap: 14px;
          padding-bottom: 12px;
          border-bottom: 1px solid var(--cream-deep);
          color: var(--ink-soft);
          font-size: 14px;
          line-height: 1.35;
        }
        .funds li:last-child { border-bottom: none; padding-bottom: 0; }
        .funds b {
          color: var(--ink);
          font-family: var(--font-display);
          font-weight: 400;
          font-size: 17px;
          text-align: right;
          white-space: nowrap;
        }
        .actions {
          margin-top: auto;
          padding-top: 24px;
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
        .primary {
          padding: 14px 22px;
          border-radius: 999px;
          background: var(--ink);
          color: var(--cream);
          font-size: 14px;
          font-weight: 500;
          letter-spacing: 0.06em;
          text-transform: uppercase;
          cursor: pointer;
          transition: transform var(--dur-fast) var(--ease-out);
        }
        .primary:active { transform: scale(0.98); }
        .ghost {
          align-self: center;
          color: var(--ink-soft);
          font-size: 12px;
          letter-spacing: 0.16em;
          text-transform: uppercase;
          text-decoration: underline;
        }
        @keyframes hero-rise {
          from { opacity: 0; transform: translateY(8px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </section>
  );
}

function formatRupees(n: number): string {
  if (!Number.isFinite(n) || n <= 0) return "₹—";
  return "₹" + Math.round(n).toLocaleString("en-IN");
}
