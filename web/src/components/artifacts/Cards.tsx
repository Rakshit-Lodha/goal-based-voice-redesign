import { inr, pct, titleCase } from "../../format";
import type { AaAssets, ExpenseBreakdown, Family, Phase, ProposedPortfolio, Ratios } from "../../types";

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
  const children = data.family?.children ?? [];
  return (
    <section>
      <div className="artifact-card-eyebrow">Family recap</div>
      <h2 className="artifact-card-title">Who Maya is planning for.</h2>
      <p className="artifact-card-lede">{data.summary ?? "Family details captured."}</p>
      <div className="artifact-metrics">
        <Metric label="Spouse age" value={data.family?.spouse_age ?? "Not added"} />
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

export function IncomeSnapshotCard({ data }: { data: IncomeData }) {
  const breakdown = data.expense_breakdown;
  return (
    <section>
      <div className="artifact-card-eyebrow">Income snapshot</div>
      <h2 className="artifact-card-title">Last three months, averaged.</h2>
      <div className="artifact-metrics">
        <Metric label="Income" value={inr(data.monthly_income)} />
        <Metric label="Outflow" value={inr(data.total_outflow)} />
        <Metric label="EMIs" value={inr(data.monthly_emi)} />
        <Metric label="EPF + NPS + stocks" value={inr(sumAssets(data.aa_assets))} />
      </div>
      {breakdown && (
        <ul className="artifact-list">
          <li><span>Investments</span><b>{inr(breakdown.investments)}</b></li>
          <li><span>Household</span><b>{inr(breakdown.household_expenses)}</b></li>
          <li><span>Utilities</span><b>{inr(breakdown.utilities)}</b></li>
          <li><span>Entertainment</span><b>{inr(breakdown.entertainment)}</b></li>
        </ul>
      )}
    </section>
  );
}

export function RatiosCard({ data }: { data: Ratios }) {
  return (
    <section>
      <div className="artifact-card-eyebrow">Cash-flow ratios</div>
      <h2 className="artifact-card-title">Savings and debt capacity.</h2>
      <div className="artifact-metrics">
        <Metric label="Savings rate" value={pct(data.savings_rate)} />
        <Metric label="Savings band" value={titleCase(data.savings_band)} />
        <Metric label="Debt-to-income" value={pct(data.debt_to_income)} />
        <Metric label="Idle surplus" value={inr(data.idle_surplus)} />
      </div>
    </section>
  );
}

export function InflationCurveCard({ data }: { data: InflationData }) {
  return (
    <section>
      <div className="artifact-card-eyebrow">{data.goal ?? "Goal"} target</div>
      <h2 className="artifact-card-title">{inr(data.inflated_target)} in {data.horizon_years ?? "-"} years</h2>
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
        Current phase {phase.phase}, {phase.duration_years} years. Future phases stay in the glide path.
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

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="artifact-metric">
      <span>{label}</span>
      <b>{value}</b>
    </div>
  );
}

function sumAssets(assets?: AaAssets) {
  if (!assets) return undefined;
  return assets.epf + assets.nps + assets.stocks;
}
