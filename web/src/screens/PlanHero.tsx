/**
 * Plan reveal — Stage 9 of 9.
 *
 * Final wrap-up. The summoned orb sits at the top; below it, the headline
 * confirms the plan is ready, a cream PDF card shows the file Maya signed,
 * and two CTAs offer the next step: Invest (primary, champagne) or
 * Download plan (ghost). Transparent background so the dark phone shell
 * shows through — matches the rest of the conversation surface.
 */
import { API_BASE } from "../pcClient";

export default function PlanHero({
  data,
  onDismiss,
}: {
  data: {
    url?: string;
    pdf_file?: string;
    total_monthly_sip?: number;
    goals_count?: number;
  };
  onDismiss: () => void;
}) {
  const pdfHref = data.url ? `${API_BASE}${data.url}` : undefined;
  const filename = data.pdf_file ?? "plan.pdf";
  const goals = data.goals_count ?? 0;
  const subtitle = goals > 0
    ? `${goals} goal${goals === 1 ? "" : "s"} · gap analysis · 4-fund SIP basket.`
    : "Your goals, gap analysis, and 4-fund SIP basket.";

  return (
    <section className="plan-hero" aria-live="polite">
      <div className="plan-hero-inner">
        <h1 className="title serif">Your wealth plan<br />is ready.</h1>
        <p className="sub">{subtitle}</p>

        <div className="pdf-card">
          <div className="pdf-icon">PDF</div>
          <div className="pdf-meta">
            <div className="filename serif">{filename}</div>
            <div className="signed">Signed by Maya · valid 30 days</div>
          </div>
        </div>

        <div className="actions">
          <button type="button" className="primary" onClick={onDismiss}>
            Invest in the portfolio
          </button>
          {pdfHref ? (
            <a className="ghost" href={pdfHref} target="_blank" rel="noreferrer">
              Download plan
            </a>
          ) : (
            <button type="button" className="ghost" disabled>
              Download plan
            </button>
          )}
        </div>
      </div>

      <style>{`
        .plan-hero {
          position: absolute;
          inset: 0;
          z-index: 8;
          padding: 240px 28px 36px;
          display: flex;
          flex-direction: column;
          color: var(--ivory);
          background: transparent;
          pointer-events: none;
          animation: hero-rise var(--dur-slow) var(--ease-out) both;
        }
        .plan-hero-inner {
          pointer-events: auto;
          display: flex;
          flex-direction: column;
          gap: 16px;
          flex: 1;
        }
        .title {
          margin: 0;
          text-align: center;
          font-size: 38px;
          line-height: 1.04;
          font-weight: 400;
          letter-spacing: -0.01em;
          color: var(--ivory);
          font-variation-settings: "opsz" 56, "wght" 400;
        }
        .sub {
          margin: 4px 0 0;
          text-align: center;
          color: var(--ink-muted, rgba(232, 230, 220, 0.55));
          font-size: 14px;
          line-height: 1.5;
          padding: 0 12px;
        }
        .pdf-card {
          margin-top: 24px;
          background: var(--cream);
          color: var(--ink);
          border-radius: 18px;
          padding: 14px 16px;
          display: flex;
          align-items: center;
          gap: 14px;
        }
        .pdf-icon {
          width: 44px;
          height: 56px;
          background: #fff;
          border: 1px solid var(--cream-deep);
          border-radius: 6px;
          display: flex;
          align-items: flex-end;
          justify-content: center;
          padding-bottom: 6px;
          font-family: var(--font-display);
          font-size: 10px;
          color: var(--ink-soft);
          letter-spacing: 0.05em;
        }
        .pdf-meta { flex: 1; min-width: 0; }
        .filename {
          font-size: 15px;
          color: var(--ink);
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .signed {
          margin-top: 3px;
          font-size: 11px;
          color: var(--ink-soft);
          letter-spacing: 0.04em;
        }
        .actions {
          margin-top: auto;
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
        .primary {
          padding: 16px 22px;
          border-radius: 999px;
          border: none;
          background: var(--champagne);
          color: var(--ink);
          font-size: 15px;
          font-weight: 500;
          letter-spacing: 0.02em;
          cursor: pointer;
          transition: transform var(--dur-fast) var(--ease-out), filter var(--dur-fast) var(--ease-out);
        }
        .primary:hover { filter: brightness(1.04); }
        .primary:active { transform: scale(0.98); }
        .ghost {
          padding: 14px 22px;
          border-radius: 999px;
          border: 1px solid rgba(232, 230, 220, 0.28);
          background: transparent;
          color: var(--ivory);
          font-size: 14px;
          font-weight: 500;
          letter-spacing: 0.02em;
          text-align: center;
          text-decoration: none;
          cursor: pointer;
          transition: background var(--dur-fast) var(--ease-out);
        }
        .ghost:hover { background: rgba(232, 230, 220, 0.06); }
        .ghost:disabled { opacity: 0.4; cursor: not-allowed; }
        @keyframes hero-rise {
          from { opacity: 0; transform: translateY(10px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </section>
  );
}
