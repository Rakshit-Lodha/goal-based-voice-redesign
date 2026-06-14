import { inr, pct, titleCase } from "../../format";
import { useStateSnapshot } from "../../state/useStateSnapshot";
import type {
  AaAssets,
  ExpenseBreakdown,
  Family,
  Phase,
  Portfolio,
  ProposedPortfolio,
  Ratios,
  Snapshot,
} from "../../types";

type RiskData = {
  risk_profile?: string;
  equity_band?: number;
  expected_return?: number;
};

type ConsentData = {
  provider?: string;
  consent_context?: string;
};

type IncomeData = {
  monthly_income?: number;
  monthly_expenses?: number;
  monthly_emi?: number;
  total_outflow?: number;
  expense_breakdown?: ExpenseBreakdown;
  aa_assets?: AaAssets;
};

type InflationData = {
  goal?: string;
  target_amount_today?: number;
  inflated_target?: number;
  projected_from_existing?: number;
  gap?: number;
  horizon_years?: number;
  required_sip?: number;
};

type InvestmentsData = {
  mf_total?: number;
  aa_assets?: AaAssets;
  manual_count?: number;
};

export function RiskRevealCard({ data }: { data: RiskData }) {
  return (
    <section>
      <div className="artifact-card-eyebrow">Your risk profile</div>
      <h2 className="artifact-card-title xl">{titleCase(data.risk_profile)}</h2>
      <p className="artifact-card-lede">
        Equity tilt and expected returns are now locked into Maya's planning math.
      </p>
      <div className="artifact-metrics">
        <Metric label="Equity band" value={pct(data.equity_band)} />
        <Metric label="Return used" value={pct(data.expected_return)} />
      </div>
    </section>
  );
}

export function FamilyRecapCard({ data }: { data: { family?: Family; summary?: string } }) {
  const snapshot = useStateSnapshot();
  const family = snapshot?.family ?? data.family;
  const children = family?.children ?? [];
  return (
    <section>
      <div className="artifact-card-eyebrow">Family recap</div>
      <h2 className="artifact-card-title">Who Maya is planning for.</h2>
      <p className="artifact-card-lede">{data.summary ?? "Family details captured."}</p>
      <div className="artifact-metrics">
        <Metric label="Spouse age" value={family?.spouse_age ?? "Not added"} />
        <Metric label="Children" value={children.length} />
      </div>
    </section>
  );
}

export function MfcConsentSheet({ data }: { data: ConsentData }) {
  return (
    <ConsentCard
      eyebrow="Consent"
      title="MF Central OTP"
      body="Maya is opening the SEBI-regulated mutual fund portfolio pull from CAMS and KFintech."
      context={data.consent_context}
    />
  );
}

export function AaConsentSheet({ data }: { data: ConsentData }) {
  return (
    <ConsentCard
      eyebrow="Consent"
      title="Finvu Account Aggregator"
      body="Let's verify your mobile number to securely fetch the bank accounts linked to this number via Account Aggregator. Powered by RBI-regulated AA and Finvu."
      context={data.consent_context}
    />
  );
}

/**
 * "What flows in, what flows out." — the cash-flow card.
 *
 * Snapshot-bound: reads monthly_income / expense_breakdown / monthly_emi
 * from the live STATE so user corrections re-render in place. The artifact
 * event payload is the fallback when snapshot hasn't arrived yet.
 */
export function IncomeSnapshotCard({ data }: { data: IncomeData }) {
  const snapshot = useStateSnapshot();
  const income = snapshot?.monthly_income ?? data.monthly_income ?? 0;
  const emi = snapshot?.monthly_emi ?? data.monthly_emi ?? 0;
  const breakdown = snapshot?.expense_breakdown ?? data.expense_breakdown ?? null;

  // Map the backend's 5-category breakdown onto the affluent reading:
  // necessary = household + utilities, discretionary = entertainment,
  // investments stays its own row, EMIs stays its own row.
  const necessary = (breakdown?.household_expenses ?? 0) + (breakdown?.utilities ?? 0);
  const discretionary = breakdown?.entertainment ?? 0;
  const investments = breakdown?.investments ?? 0;
  const totalOutflow = necessary + discretionary + investments + emi;

  const rows: Array<{ label: string; value: number }> = [
    { label: "Household income", value: income },
    { label: "Discretionary spend", value: discretionary },
    { label: "Necessary spend", value: necessary },
    { label: "Investments", value: investments },
    { label: "EMIs", value: emi },
  ];

  return (
    <section className="cashflow">
      <div className="artifact-card-eyebrow">Your monthly snapshot</div>
      <h2 className="artifact-card-title xl">
        What flows in,<br />what flows out.
      </h2>

      <ul className="cashflow-rows">
        {rows.map((row) => (
          <li key={row.label}>
            <span>{row.label}</span>
            <b>{inr(row.value)}</b>
          </li>
        ))}
      </ul>

      <div className="cashflow-total">
        <span>Total outflow</span>
        <b>{inr(totalOutflow)}</b>
      </div>

      <style>{`
        .cashflow .artifact-card-title.xl { font-size: 36px; line-height: 1.04; max-width: none; }
        .cashflow-rows {
          margin: 24px 0 0;
          padding: 0;
          list-style: none;
          display: grid;
          gap: 0;
        }
        .cashflow-rows li {
          display: flex;
          align-items: baseline;
          justify-content: space-between;
          gap: 14px;
          padding: 16px 0;
          border-bottom: 1px solid var(--cream-deep);
          color: var(--ink-soft);
          font-size: 15px;
          line-height: 1.2;
        }
        .cashflow-rows li b {
          color: var(--ink);
          font-family: var(--font-display);
          font-weight: 400;
          font-size: 17px;
        }
        .cashflow-total {
          margin-top: 4px;
          padding-top: 22px;
          border-top: 2px solid var(--ink);
          display: flex;
          align-items: baseline;
          justify-content: space-between;
          gap: 14px;
          color: var(--ink);
          font-size: 15px;
          font-weight: 500;
        }
        .cashflow-total b {
          color: var(--champagne);
          font-family: var(--font-display);
          font-weight: 400;
          font-size: 36px;
          letter-spacing: -0.01em;
        }
      `}</style>
    </section>
  );
}

/**
 * "Healthy across the board." — the financial posture card.
 *
 * Two horizontal zone bars with a dot at the live value, an uppercased
 * band badge on the right, and the idle-surplus close-out at the bottom.
 * Snapshot-bound for live updates after a correction.
 */
export function RatiosCard({ data }: { data: Ratios }) {
  const snapshot = useStateSnapshot();
  const ratios = snapshot?.ratios ?? data;

  const sRate = ratios.savings_rate ?? 0;
  const dRate = ratios.debt_to_income ?? 0;

  const sBand = (ratios.savings_band ?? "average").toLowerCase();
  const dBand = (ratios.dti_band ?? "average").toLowerCase();

  const title = sBand === "good" && dBand === "good"
    ? "Healthy across the board."
    : "Worth a closer look.";

  return (
    <section className="posture">
      <div className="artifact-card-eyebrow">Your financial posture</div>
      <h2 className="artifact-card-title xl">{title}</h2>

      <PostureRow
        label="Savings rate"
        valueLabel={`${Math.round(sRate * 100)} %`}
        bandLabel={sBand.toUpperCase()}
        bandTone={bandTone(sBand)}
        zonePosition={Math.min(1, Math.max(0, sRate))}
        zones={["Low", "Healthy", "Strong"]}
      />

      <PostureRow
        label="Debt-to-income"
        valueLabel={`${Math.round(dRate * 100)} %`}
        bandLabel={dtiBadge(dBand)}
        bandTone={bandTone(dBand, true)}
        // DTI bar visually spans 0–30% — anything past 30% sits at the end.
        zonePosition={Math.min(1, Math.max(0, dRate / 0.30))}
        zones={["Comfortable", "Watch", "High"]}
      />

      <p className="posture-foot">
        You have {inr(ratios.idle_surplus)}/month in idle surplus.
        Maya will route this toward your goals.
      </p>

      <style>{`
        .posture .artifact-card-title.xl { font-size: 36px; line-height: 1.04; max-width: none; }
        .posture-foot {
          margin: 22px 0 0;
          color: var(--ink-soft);
          font-size: 13px;
          line-height: 1.5;
        }
      `}</style>
    </section>
  );
}

function PostureRow({
  label,
  valueLabel,
  bandLabel,
  bandTone,
  zonePosition,
  zones,
}: {
  label: string;
  valueLabel: string;
  bandLabel: string;
  bandTone: "good" | "warn" | "bad";
  zonePosition: number; // 0..1
  zones: [string, string, string];
}) {
  const left = `${(zonePosition * 100).toFixed(1)}%`;
  return (
    <div className="posture-row">
      <div className="posture-head">
        <span className="posture-label">{label}</span>
        <span className="posture-value">
          <span className="posture-num">{valueLabel}</span>
          <span className={`posture-badge tone-${bandTone}`}>{bandLabel}</span>
        </span>
      </div>
      <div className="posture-bar">
        <div className="posture-bar-fill" style={{ width: left }} />
        <div className="posture-bar-dot" style={{ left }} />
      </div>
      <div className="posture-zones">
        {zones.map((z) => <span key={z}>{z}</span>)}
      </div>

      <style>{`
        .posture-row {
          margin-top: 26px;
        }
        .posture-head {
          display: flex;
          align-items: baseline;
          justify-content: space-between;
          gap: 14px;
        }
        .posture-label {
          color: var(--ink-soft);
          font-size: 15px;
        }
        .posture-value {
          display: inline-flex;
          align-items: baseline;
          gap: 10px;
        }
        .posture-num {
          color: var(--ink);
          font-family: var(--font-display);
          font-weight: 400;
          font-size: 28px;
          letter-spacing: -0.01em;
        }
        .posture-badge {
          font-size: 11px;
          letter-spacing: 0.12em;
          text-transform: uppercase;
          font-weight: 500;
        }
        .tone-good { color: var(--green); }
        .tone-warn { color: var(--amber); }
        .tone-bad  { color: #B14A2A; }
        .posture-bar {
          position: relative;
          height: 6px;
          margin-top: 10px;
          background: var(--cream-deep);
          border-radius: 999px;
        }
        .posture-bar-fill {
          position: absolute;
          inset: 0 auto 0 0;
          background: linear-gradient(90deg, var(--green) 0%, var(--green-soft) 100%);
          border-radius: 999px;
        }
        .posture-bar-dot {
          position: absolute;
          top: 50%;
          width: 16px;
          height: 16px;
          margin-left: -8px;
          background: var(--cream);
          border: 1.5px solid var(--ink);
          border-radius: 50%;
          transform: translateY(-50%);
        }
        .posture-zones {
          margin-top: 8px;
          display: flex;
          justify-content: space-between;
          color: var(--ink-soft);
          font-size: 10px;
          letter-spacing: 0.18em;
          text-transform: uppercase;
        }
      `}</style>
    </div>
  );
}

function bandTone(band: string, dti: boolean = false): "good" | "warn" | "bad" {
  if (band === "good") return dti ? "good" : "good";
  if (band === "average") return "warn";
  return "bad";
}

function dtiBadge(band: string): string {
  // Friendlier badges for the DTI axis since "BAD" reads weird as a DTI label.
  if (band === "good") return "LOW";
  if (band === "average") return "WATCH";
  return "HIGH";
}

/**
 * Investments review — parallel to the cash-flow card.
 *
 * Lists the user's investments by source (MF portfolio, EPF, NPS, Stocks,
 * each manual asset) and tallies the total. Snapshot-bound, so EPF/NPS/
 * stocks edits from "pull_account_aggregator with correction" land here
 * without needing the artifact event to be re-summoned.
 */
export function InvestmentsCard(_props: { data: InvestmentsData }) {
  const snapshot = useStateSnapshot();
  if (!snapshot) {
    return (
      <section>
        <div className="artifact-card-eyebrow">Your investments</div>
        <h2 className="artifact-card-title xl">Where your money is parked.</h2>
        <p className="artifact-card-lede">Waiting for the live snapshot…</p>
      </section>
    );
  }

  const portfolio: Portfolio | null = snapshot.portfolio;
  const aa = snapshot.aa_assets;
  const manuals = snapshot.additional_assets ?? [];

  const rows: Array<{ label: string; value: number; sub?: string }> = [];
  if (portfolio && portfolio.total_value > 0) {
    rows.push({
      label: "Mutual fund portfolio",
      value: portfolio.total_value,
      sub: `${portfolio.holdings.length} fund${portfolio.holdings.length === 1 ? "" : "s"}`,
    });
  }
  if (aa) {
    if (aa.epf > 0) rows.push({ label: "EPF", value: aa.epf });
    if (aa.nps > 0) rows.push({ label: "NPS", value: aa.nps });
    if (aa.stocks > 0) rows.push({ label: "Stocks", value: aa.stocks });
  }
  for (const m of manuals) {
    rows.push({ label: m.name, value: m.value, sub: titleCase(m.asset_type) });
  }

  const total = rows.reduce((sum, r) => sum + r.value, 0);

  return (
    <section className="investments">
      <div className="artifact-card-eyebrow">Your investments</div>
      <h2 className="artifact-card-title xl">
        Where your<br />money is parked.
      </h2>

      {rows.length === 0 ? (
        <p className="artifact-card-lede">Nothing on file yet. Maya will pull MF + AA next.</p>
      ) : (
        <ul className="investments-rows">
          {rows.map((row) => (
            <li key={row.label}>
              <span className="row-label">
                <span>{row.label}</span>
                {row.sub && <em>{row.sub}</em>}
              </span>
              <b>{inr(row.value)}</b>
            </li>
          ))}
        </ul>
      )}

      <div className="investments-total">
        <span>Total invested</span>
        <b>{inr(total)}</b>
      </div>

      <style>{`
        .investments .artifact-card-title.xl { font-size: 36px; line-height: 1.04; max-width: none; }
        .investments-rows {
          margin: 24px 0 0;
          padding: 0;
          list-style: none;
          display: grid;
          gap: 0;
        }
        .investments-rows li {
          display: flex;
          align-items: baseline;
          justify-content: space-between;
          gap: 14px;
          padding: 16px 0;
          border-bottom: 1px solid var(--cream-deep);
          color: var(--ink-soft);
          font-size: 15px;
          line-height: 1.2;
        }
        .investments-rows .row-label { display: inline-flex; flex-direction: column; gap: 2px; }
        .investments-rows .row-label em {
          font-style: normal;
          color: var(--ink-soft);
          font-size: 11px;
          letter-spacing: 0.12em;
          text-transform: uppercase;
          opacity: 0.7;
        }
        .investments-rows li b {
          color: var(--ink);
          font-family: var(--font-display);
          font-weight: 400;
          font-size: 17px;
        }
        .investments-total {
          margin-top: 4px;
          padding-top: 22px;
          border-top: 2px solid var(--ink);
          display: flex;
          align-items: baseline;
          justify-content: space-between;
          gap: 14px;
          color: var(--ink);
          font-size: 15px;
          font-weight: 500;
        }
        .investments-total b {
          color: var(--champagne);
          font-family: var(--font-display);
          font-weight: 400;
          font-size: 36px;
          letter-spacing: -0.01em;
        }
      `}</style>
    </section>
  );
}

export function InflationCurveCard({ data }: { data: InflationData }) {
  return (
    <section>
      <div className="artifact-card-eyebrow">{data.goal ?? "Goal"} target</div>
      <h2 className="artifact-card-title">{inr(data.inflated_target)} in {yearsLabel(data.horizon_years)}</h2>
      <svg className="artifact-curve" viewBox="0 0 320 110" role="img" aria-label="Inflation curve">
        <defs>
          <linearGradient id="curveFill" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="#C9A961" stopOpacity="0.35" />
            <stop offset="100%" stopColor="#C9A961" stopOpacity="0" />
          </linearGradient>
        </defs>
        <line x1="0" y1="100" x2="320" y2="100" stroke="#D8CFBC" />
        <path d="M 0 90 Q 100 86 160 68 T 320 14 L 320 100 L 0 100 Z" fill="url(#curveFill)" />
        <path d="M 0 90 Q 100 86 160 68 T 320 14" stroke="#B89548" strokeWidth="2" fill="none" />
        <circle cx="0" cy="90" r="3.5" fill="#1A1F2E" />
        <circle cx="320" cy="14" r="4.5" fill="#C9A961" />
      </svg>
      <div className="artifact-metrics">
        <Metric label="Today" value={inr(data.target_amount_today)} />
        <Metric label="SIP needed" value={inr(data.required_sip)} />
        <Metric label="Existing corpus" value={inr(data.projected_from_existing)} />
        <Metric label="Gap" value={inr(data.gap)} />
      </div>
    </section>
  );
}

export function SipSplitCard({ data }: { data: ProposedPortfolio }) {
  const phase = data.current_phase;
  return (
    <section>
      <div className="artifact-card-eyebrow">{data.goal}</div>
      <h2 className="artifact-card-title">{inr(data.monthly_sip)} monthly SIP</h2>
      <p className="artifact-card-lede">
        Current phase {phase.phase}, {yearsLabel(phase.duration_years)}. Future phases stay in the glide path.
      </p>
      <div className="artifact-metrics">
        <Metric label="Equity" value={pct(phase.allocation.equity)} />
        <Metric label="Debt" value={pct(phase.allocation.debt)} />
        <Metric label="Gold" value={pct(phase.allocation.gold)} />
        <Metric label="Horizon" value={titleCase(data.horizon_bucket)} />
      </div>
      <FundList phase={phase} />
    </section>
  );
}

export function FundsPickerSheet({ data }: { data: ProposedPortfolio }) {
  return (
    <section>
      <div className="artifact-card-eyebrow">Funds picker</div>
      <h2 className="artifact-card-title">{data.goal ?? "Goal"} funds</h2>
      <p className="artifact-card-lede">{data.selection_basis ?? "Maya will show the selected funds here."}</p>
      {data.current_phase && <FundList phase={data.current_phase} />}
    </section>
  );
}

export function SipPlanFallback({ data }: { data: { total_monthly_sip?: number } }) {
  return (
    <section>
      <div className="artifact-card-eyebrow">Plan ready</div>
      <h2 className="artifact-card-title">Your plan is ready.</h2>
      <p className="artifact-card-lede">
        Phase 6 will turn this into the full hero reveal. For now, Maya has generated the plan.
      </p>
      {data.total_monthly_sip !== undefined && (
        <div className="artifact-metrics">
          <Metric label="Total SIP" value={inr(data.total_monthly_sip)} />
        </div>
      )}
    </section>
  );
}

function ConsentCard({
  eyebrow,
  title,
  body,
  context,
}: {
  eyebrow: string;
  title: string;
  body: string;
  context?: string;
}) {
  return (
    <section>
      <div className="artifact-card-eyebrow">{eyebrow}</div>
      <h2 className="artifact-card-title">{title}</h2>
      <p className="artifact-card-lede">{body}</p>
      {context && <p className="artifact-card-lede">{context}</p>}
    </section>
  );
}

function FundList({ phase }: { phase: Phase }) {
  if (!phase.funds?.length) return null;
  return (
    <ul className="artifact-list">
      {phase.funds.map((fund) => (
        <li key={`${phase.phase}-${fund.fund}`}>
          <span>{fund.fund}</span>
          <b>{inr(fund.monthly_sip)}</b>
        </li>
      ))}
    </ul>
  );
}

function yearsLabel(years?: number) {
  if (years === undefined || years === null) return "-";
  return `${years} ${years === 1 ? "year" : "years"}`;
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="artifact-metric">
      <span>{label}</span>
      <b>{value}</b>
    </div>
  );
}

// Re-export to keep the registry happy with the public surface; kept for
// snapshot-less consumers that still want the AA assets sum.
export function _sumAssets(snap: Snapshot | null): number {
  if (!snap?.aa_assets) return 0;
  const { epf, nps, stocks } = snap.aa_assets;
  return epf + nps + stocks;
}
