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
  ratios?: Ratios;
};

type InflationData = {
  goal?: string;
  target_amount_today?: number;
  inflated_target?: number;
  projected_from_existing?: number;
  gap?: number;
  horizon_years?: number;
  required_sip?: number;
  inflation_used?: number;
  target_year?: number;
};

type InvestmentsData = {
  mf_total?: number;
  aa_assets?: AaAssets;
  manual_count?: number;
};

type MfcReviewData = {
  total_funds?: number;
  total_value?: number;
  total_monthly_sip?: number;
  underperformer_count?: number;
  good_count?: number;
  insights?: Array<{ tone: "good" | "warn" | "bad"; text: string }>;
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

/**
 * MFC review — the diagnostic moment after MF Central returns.
 *
 * Eyebrow + Fraunces title + lede frame the verdict; three metrics
 * (Total funds · Monthly SIP · Underperformers) carry the numbers;
 * a pinned insight list translates fund_reviews into three plain
 * sentences with tone-coloured icons.
 */
export function MfcReviewCard({ data }: { data: MfcReviewData }) {
  const totalFunds = data.total_funds ?? 0;
  const monthlySip = data.total_monthly_sip ?? 0;
  const underperformers = data.underperformer_count ?? 0;
  const insights = data.insights ?? [];

  const title = underperformers > 0
    ? "Your portfolio is invested, but not yet intentional."
    : "A clean portfolio.";
  const lede = underperformers > 0
    ? `Maya found good exposure, but ${underperformers} fund${underperformers === 1 ? "" : "s"} ${underperformers === 1 ? "is" : "are"} dragging the portfolio. Time to clean up.`
    : "No red flags. Maya will reuse what fits and route the rest to your goals.";

  return (
    <section className="mfc-review">
      <div className="artifact-card-eyebrow">MF Central diagnosis</div>
      <h2 className="artifact-card-title">{title}</h2>
      <p className="artifact-card-lede">{lede}</p>

      <div className="mfc-metrics">
        <Metric label="Total funds" value={totalFunds} />
        <Metric label="Monthly SIP" value={inr(monthlySip)} />
        <Metric
          label={underperformers > 0 ? "Need review" : "Good funds"}
          value={underperformers > 0 ? underperformers : data.good_count ?? 0}
        />
      </div>

      {insights.length > 0 && (
        <ul className="mfc-insights">
          {insights.map((insight, i) => (
            <li key={i}>
              <span className={`pin tone-${insight.tone}`}>
                {insight.tone === "good" ? "✓" : insight.tone === "warn" ? "!" : "×"}
              </span>
              <span>{insight.text}</span>
            </li>
          ))}
        </ul>
      )}

      <style>{`
        .mfc-review .artifact-card-title { max-width: none; }
        .mfc-metrics {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 10px;
          margin-top: 18px;
        }
        .mfc-insights {
          margin: 16px 0 0;
          padding: 0;
          list-style: none;
          display: grid;
          gap: 0;
        }
        .mfc-insights li {
          display: grid;
          grid-template-columns: 24px 1fr;
          gap: 12px;
          align-items: flex-start;
          padding: 12px 0;
          border-bottom: 1px solid var(--cream-deep);
          color: var(--ink-soft);
          font-size: 13px;
          line-height: 1.42;
        }
        .mfc-insights li:last-child { border-bottom: none; }
        .pin {
          width: 22px;
          height: 22px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 12px;
          font-weight: 500;
          line-height: 1;
        }
        .pin.tone-good { background: var(--green); color: var(--cream); }
        .pin.tone-warn { background: var(--champagne); color: var(--ink); }
        .pin.tone-bad  { background: #B14A2A; color: var(--cream); }
      `}</style>
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
  const ratios = snapshot?.ratios ?? data.ratios ?? null;

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

  const sRate = ratios?.savings_rate ?? 0;
  const dRate = ratios?.debt_to_income ?? 0;
  const sBand = (ratios?.savings_band ?? "average").toLowerCase();
  const dBand = (ratios?.dti_band ?? "average").toLowerCase();

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

      {ratios && (
        <div className="cashflow-posture">
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
            zonePosition={Math.min(1, Math.max(0, dRate / 0.30))}
            zones={["Comfortable", "Watch", "High"]}
          />
          <p className="posture-foot">
            You have {inr(ratios.idle_surplus)}/month in idle surplus.
            Maya will route this toward your goals.
          </p>
        </div>
      )}

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
        .cashflow-posture { margin-top: 30px; }
        .cashflow-posture .posture-foot {
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

/**
 * Goal-types picker — emitted as Stage 5 opens.
 *
 * Visual menu of the six goal categories Maya plans, grouped by Safety /
 * Long-term independence / Aspirations. Two are tagged "Recommended" — the
 * defaults Maya auto-plans for every caller (Emergency, Retirement). Not
 * interactive (voice drives the conversation); this is the visual anchor
 * while Maya frames the goals stage.
 */
type GoalType = {
  key: string;
  label: string;
  section: string;
  blurb: string;
};

export function GoalTypesPickerCard({
  data,
}: {
  data: { types?: GoalType[]; recommended?: string[] };
}) {
  const types = data.types ?? [];
  const recommended = new Set(data.recommended ?? []);
  const sections: string[] = [];
  const byKey = new Map<string, GoalType[]>();
  for (const t of types) {
    if (!byKey.has(t.section)) {
      sections.push(t.section);
      byKey.set(t.section, []);
    }
    byKey.get(t.section)!.push(t);
  }

  return (
    <section className="goal-picker">
      <div className="artifact-card-eyebrow">Stage three of three</div>
      <h2 className="artifact-card-title xl">
        What are we<br />planning for?
      </h2>
      <p className="artifact-card-lede">
        Three buckets, six common goals. Maya plans the first two by default —
        the rest, you choose by speaking.
      </p>

      <div className="picker-sections">
        {sections.map((section) => (
          <div key={section} className="picker-section">
            <div className="picker-section-label">{section}</div>
            <ul className="picker-rows">
              {byKey.get(section)!.map((t) => (
                <li key={t.key}>
                  <div className="picker-row-head">
                    <span className="picker-name">{t.label}</span>
                    {recommended.has(t.key) && (
                      <span className="picker-tag">Recommended</span>
                    )}
                  </div>
                  <p className="picker-blurb">{t.blurb}</p>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      <style>{`
        .goal-picker .artifact-card-title.xl { font-size: 36px; line-height: 1.04; max-width: none; }
        .picker-sections {
          margin-top: 22px;
          display: grid;
          gap: 18px;
        }
        .picker-section-label {
          color: var(--ink-soft);
          font-size: 10px;
          letter-spacing: 0.18em;
          text-transform: uppercase;
          margin-bottom: 6px;
        }
        .picker-rows {
          margin: 0;
          padding: 0;
          list-style: none;
          display: grid;
          gap: 0;
        }
        .picker-rows li {
          padding: 12px 0;
          border-bottom: 1px solid var(--cream-deep);
        }
        .picker-rows li:last-child { border-bottom: none; }
        .picker-row-head {
          display: flex;
          align-items: baseline;
          justify-content: space-between;
          gap: 10px;
        }
        .picker-name {
          font-family: var(--font-display);
          font-size: 17px;
          color: var(--ink);
        }
        .picker-tag {
          font-size: 9px;
          letter-spacing: 0.16em;
          text-transform: uppercase;
          color: #B89548;
          background: rgba(201, 169, 97, 0.16);
          border-radius: 999px;
          padding: 3px 8px;
        }
        .picker-blurb {
          margin: 4px 0 0;
          color: var(--ink-soft);
          font-size: 12px;
          line-height: 1.45;
        }
      `}</style>
    </section>
  );
}

/**
 * Goals recap — the "Where we're heading" card.
 *
 * On-demand summary of every captured goal. Maya summons it via
 * show_artifact("goals_recap") when the user asks "what are we planning"
 * or any equivalent. Snapshot-bound so reprioritizations show through.
 */
type GoalsRecapRow = {
  name: string;
  priority: number;
  horizon_years: number;
  target_year: number;
  target_amount_today: number;
  inflated_target: number;
  required_sip: number | null;
  funded: boolean;
};

export function GoalsRecapCard({
  data,
}: {
  data: { goals?: GoalsRecapRow[]; total_inflated?: number; total_sip?: number };
}) {
  const snapshot = useStateSnapshot();
  // Prefer live snapshot so reprioritize edits show through without a
  // re-summon. Falls back to the payload when snapshot isn't ready.
  const liveGoals = snapshot?.goals ?? [];
  const rows: GoalsRecapRow[] = liveGoals.length > 0
    ? liveGoals
        .slice()
        .sort((a, b) => a.priority - b.priority)
        .map((g) => ({
          name: g.name,
          priority: g.priority,
          horizon_years: g.horizon_years,
          target_year: new Date().getFullYear() + g.horizon_years,
          target_amount_today: g.target_amount_today,
          inflated_target: g.inflated_target ?? g.target_amount_today,
          required_sip: g.required_sip,
          funded: g.funded,
        }))
    : data.goals ?? [];
  const totalInflated = rows.reduce((s, g) => s + (g.inflated_target ?? 0), 0);
  const totalSip = rows.reduce(
    (s, g) => s + (g.funded ? g.required_sip ?? 0 : 0),
    0,
  );
  const latestYear = rows.reduce((y, g) => Math.max(y, g.target_year), 0);

  return (
    <section className="goals-recap">
      <div className="artifact-card-eyebrow">Goals in flight</div>
      <h2 className="artifact-card-title xl">
        Where we're<br />heading.
      </h2>
      <p className="artifact-card-lede">
        {rows.length} goal{rows.length === 1 ? "" : "s"}, anchored end-to-end.
        Maya keeps the priorities honest as numbers shift.
      </p>

      <ul className="recap-rows">
        {rows.map((g) => (
          <li key={`${g.priority}-${g.name}`}>
            <span className="recap-priority">{g.priority}</span>
            <div className="recap-meta">
              <div className="recap-name">{g.name}</div>
              <div className="recap-horizon">
                {g.horizon_years} yr · {g.target_year}
                {g.required_sip ? ` · ${inr(g.required_sip)}/mo` : ""}
                {!g.funded && rows.length > 1 ? " · parked" : ""}
              </div>
            </div>
            <b className="recap-target">{inr(g.inflated_target)}</b>
          </li>
        ))}
      </ul>

      <div className="recap-total">
        <div>
          <span>Total target {latestYear ? `by ${latestYear}` : ""}</span>
          <b>{inr(totalInflated)}</b>
        </div>
        {totalSip > 0 && (
          <div>
            <span>Combined monthly SIP</span>
            <b className="recap-sip">{inr(totalSip)}</b>
          </div>
        )}
      </div>

      <style>{`
        .goals-recap .artifact-card-title.xl { font-size: 36px; line-height: 1.04; max-width: none; }
        .recap-rows {
          margin: 22px 0 0;
          padding: 0;
          list-style: none;
        }
        .recap-rows li {
          display: grid;
          grid-template-columns: 28px 1fr auto;
          gap: 12px;
          align-items: center;
          padding: 14px 0;
          border-bottom: 1px solid var(--cream-deep);
        }
        .recap-rows li:last-child { border-bottom: none; }
        .recap-priority {
          width: 28px;
          height: 28px;
          border-radius: 50%;
          background: var(--ink);
          color: var(--cream);
          display: inline-flex;
          align-items: center;
          justify-content: center;
          font-family: var(--font-display);
          font-size: 13px;
        }
        .recap-meta { min-width: 0; }
        .recap-name {
          font-family: var(--font-display);
          font-size: 16px;
          color: var(--ink);
        }
        .recap-horizon {
          margin-top: 2px;
          color: var(--ink-soft);
          font-size: 11px;
          letter-spacing: 0.06em;
          text-transform: uppercase;
        }
        .recap-target {
          font-family: var(--font-display);
          font-weight: 400;
          font-size: 18px;
          color: var(--ink);
          white-space: nowrap;
        }
        .recap-total {
          margin-top: 6px;
          padding-top: 18px;
          border-top: 2px solid var(--ink);
          display: grid;
          gap: 14px;
        }
        .recap-total > div {
          display: flex;
          align-items: baseline;
          justify-content: space-between;
          gap: 14px;
        }
        .recap-total span {
          color: var(--ink);
          font-size: 13px;
          font-weight: 500;
        }
        .recap-total b {
          color: var(--ink);
          font-family: var(--font-display);
          font-weight: 400;
          font-size: 28px;
          letter-spacing: -0.01em;
        }
        .recap-total b.recap-sip { color: var(--champagne); }
      `}</style>
    </section>
  );
}

export function InflationCurveCard({ data }: { data: InflationData }) {
  const snapshot = useStateSnapshot();
  // Prefer live snapshot values for the named goal so updates from
  // compute_gap_and_sip flow in without re-summoning the artifact.
  const liveGoal = snapshot?.goals.find((g) => g.name === data.goal);
  const targetToday = data.target_amount_today ?? 0;
  const targetFuture = liveGoal?.inflated_target ?? data.inflated_target ?? targetToday;
  const horizon = data.horizon_years ?? 1;
  const inflation = data.inflation_used ?? 0;
  const year = data.target_year ?? new Date().getFullYear() + horizon;
  const todayYear = year - horizon;
  const sip = liveGoal?.required_sip ?? data.required_sip ?? null;

  const eyebrow = `${(data.goal ?? "Goal").toUpperCase()} · ${year}`;
  const inflPct = Math.round(inflation * 100);
  const description = inflation > 0
    ? `${assetClass(data.goal)} compound at ~${inflPct}% a year. ${inr(targetToday)} today will cost ${inr(targetFuture)} by ${year}.`
    : `${inr(targetToday)} set aside as a safety net for the next ${horizon} year${horizon === 1 ? "" : "s"}.`;

  return (
    <section className="inflation-curve">
      <div className="artifact-card-eyebrow">{eyebrow}</div>
      <h2 className="artifact-card-title xl">{inr(targetFuture)}</h2>
      <p className="artifact-card-lede">{description}</p>

      <CurveChart
        startYear={todayYear}
        startValue={targetToday}
        endValue={targetFuture}
      />

      <div className="curve-boxes">
        <div className="curve-box">
          <span>Today</span>
          <b>{inr(targetToday)}</b>
        </div>
        <div className="curve-box">
          <span>In {horizon} year{horizon === 1 ? "" : "s"}</span>
          <b>{inr(targetFuture)}</b>
        </div>
      </div>

      {sip ? (
        <p className="curve-foot">
          Monthly SIP for this goal · <b>{inr(sip)}</b>
        </p>
      ) : null}

      <style>{`
        .inflation-curve .artifact-card-title.xl {
          font-size: 56px;
          line-height: 1;
          letter-spacing: -0.02em;
          margin-top: 4px;
        }
        .inflation-curve .artifact-card-lede {
          margin-top: 16px;
          color: var(--ink-soft);
          font-size: 14px;
          line-height: 1.5;
        }
        .curve-boxes {
          margin-top: 20px;
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 10px;
        }
        .curve-box {
          background: var(--cream-deep);
          border-radius: 14px;
          padding: 14px 16px;
          display: flex;
          flex-direction: column;
          gap: 6px;
        }
        .curve-box span {
          color: var(--ink-soft);
          font-size: 11px;
          letter-spacing: 0.14em;
          text-transform: uppercase;
        }
        .curve-box b {
          font-family: var(--font-display);
          font-weight: 400;
          font-size: 22px;
          color: var(--ink);
          letter-spacing: -0.01em;
        }
        .curve-foot {
          margin: 18px 0 0;
          font-size: 13px;
          color: var(--ink-soft);
        }
        .curve-foot b {
          color: var(--champagne);
          font-family: var(--font-display);
          font-weight: 400;
          font-size: 15px;
        }
        .curve-foot.muted { font-style: italic; }
      `}</style>
    </section>
  );
}

function assetClass(goalName?: string): string {
  const n = (goalName ?? "").toLowerCase();
  if (/education|college|school|study|studies|mba|degree/.test(n)) return "Education costs";
  if (/house|home|property|flat|apartment|plot/.test(n)) return "Property prices";
  if (/car|vehicle|bike/.test(n)) return "Vehicle prices";
  return "Costs";
}

/**
 * Inflation curve chart — exponential growth from start year/value to end
 * year/value. Computed from inflation rate; if the rate is zero, falls back
 * to a flat line. Endpoints labelled below the curve.
 */
function CurveChart({ startYear, startValue, endValue }:
  { startYear: number; startValue: number; endValue: number }) {
  const W = 320;
  const H = 140;
  const padX = 24;
  const padTop = 18;
  const padBot = 30;
  const usableW = W - padX * 2;
  const usableH = H - padTop - padBot;

  // Build curve as an exponential between (0, startValue) and (1, endValue).
  // value(t) = startValue * (endValue/startValue)^t
  const ratio = startValue > 0 ? endValue / startValue : 1;
  const pts: Array<[number, number]> = [];
  const N = 24;
  for (let i = 0; i <= N; i++) {
    const t = i / N;
    const v = startValue * Math.pow(ratio, t);
    const x = padX + t * usableW;
    const y = padTop + (1 - (v - startValue) / Math.max(1, endValue - startValue)) * usableH;
    pts.push([x, y]);
  }
  const path = pts.map(([x, y], i) => `${i === 0 ? "M" : "L"} ${x.toFixed(1)} ${y.toFixed(1)}`).join(" ");
  const fill = `${path} L ${padX + usableW} ${padTop + usableH} L ${padX} ${padTop + usableH} Z`;
  const [x0, y0] = pts[0];
  const [x1, y1] = pts[pts.length - 1];

  return (
    <svg className="curve-svg" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Inflation curve">
      <defs>
        <linearGradient id="curveFill" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor="#C9A961" stopOpacity="0.30" />
          <stop offset="100%" stopColor="#C9A961" stopOpacity="0" />
        </linearGradient>
      </defs>
      {/* dashed baseline + midline */}
      <line x1={padX} y1={padTop + usableH} x2={padX + usableW} y2={padTop + usableH}
            stroke="#D8CFBC" strokeDasharray="3 4" />
      <line x1={padX} y1={padTop + usableH / 2} x2={padX + usableW} y2={padTop + usableH / 2}
            stroke="#E6DCC4" strokeDasharray="3 4" />

      <path d={fill} fill="url(#curveFill)" />
      <path d={path} stroke="#B89548" strokeWidth="2.5" fill="none" strokeLinecap="round" />

      {/* start point */}
      <circle cx={x0} cy={y0} r="4" fill="#1A1F2E" />
      <text x={x0 + 10} y={y0 + 14} className="curve-label">
        {startYear} · {inr(startValue)}
      </text>

      {/* end point */}
      <circle cx={x1} cy={y1} r="5" fill="#C9A961" />
      <text x={x1 - 6} y={y1 - 10} textAnchor="end" className="curve-label end">
        {inr(endValue)}
      </text>

      <style>{`
        .curve-svg { display: block; width: 100%; margin-top: 22px; }
        .curve-label {
          fill: var(--ink-soft);
          font-size: 10px;
          letter-spacing: 0.04em;
          font-family: var(--font-sans);
        }
        .curve-label.end { fill: var(--champagne); font-weight: 600; }
      `}</style>
    </svg>
  );
}

/**
 * SIP split — the recommendation thesis + action list for a goal.
 *
 * Donut ring shows the current phase's equity/debt/gold split with the
 * monthly SIP at the centre. Fund rows below carry Keep / Add tags
 * derived by matching the proposed fund name against existing MF
 * Central holdings. The whole card is snapshot-aware so tags update
 * if the user adds or removes a fund mid-call.
 */
export function SipSplitCard({ data }: { data: ProposedPortfolio }) {
  const snapshot = useStateSnapshot();
  const phase = data.current_phase;
  const existingNames = new Set(
    (snapshot?.portfolio?.holdings ?? []).map((h) => h.fund.toLowerCase()),
  );

  return (
    <section className="sip-split">
      <div className="artifact-card-eyebrow">{data.goal} · target basket</div>
      <h2 className="artifact-card-title xl">{inr(data.monthly_sip)} monthly SIP</h2>
      <p className="artifact-card-lede">
        Current phase {phase.phase}, {yearsLabel(phase.duration_years)}.
        Each rupee has a role: growth, stability, and a gold hedge.
      </p>

      <div className="sip-thesis">
        <AllocationRing
          equity={phase.allocation.equity}
          debt={phase.allocation.debt}
          gold={phase.allocation.gold}
          centerLabel={inr(data.monthly_sip)}
        />
        <div className="sip-legend">
          <LegendRow swatch="champagne" label="Equity" value={pct(phase.allocation.equity)} />
          <LegendRow swatch="green"     label="Debt"   value={pct(phase.allocation.debt)} />
          <LegendRow swatch="ink"       label="Gold"   value={pct(phase.allocation.gold)} />
          <LegendRow swatch="soft"      label="Horizon" value={titleCase(data.horizon_bucket)} />
        </div>
      </div>

      {phase.funds?.length ? (
        <ul className="fund-stack">
          {phase.funds.map((fund) => {
            const isExisting = existingNames.has(fund.fund.toLowerCase());
            return (
              <li key={`${phase.phase}-${fund.fund}`}>
                <span className={`tag ${isExisting ? "keep" : "add"}`}>
                  {isExisting ? "Keep" : "Add"}
                </span>
                <div className="fund-name">
                  <span>{fund.fund}</span>
                  <small>{titleCase(fund.bucket)} · {fund.rationale}</small>
                </div>
                <b className="amount">{inr(fund.monthly_sip)}</b>
              </li>
            );
          })}
        </ul>
      ) : null}

      <style>{`
        .sip-split .artifact-card-title.xl { font-size: 36px; color: var(--champagne); }
        .sip-thesis {
          display: grid;
          grid-template-columns: 118px 1fr;
          gap: 18px;
          align-items: center;
          margin-top: 22px;
        }
        .sip-legend { display: grid; gap: 0; }
        .fund-stack {
          margin: 18px 0 0;
          padding: 0;
          list-style: none;
          border-top: 1px solid var(--cream-deep);
        }
        .fund-stack li {
          display: grid;
          grid-template-columns: 64px 1fr auto;
          gap: 12px;
          align-items: center;
          padding: 12px 0;
          border-bottom: 1px solid var(--cream-deep);
        }
        .fund-stack li:last-child { border-bottom: none; }
        .tag {
          width: fit-content;
          min-width: 50px;
          border-radius: 999px;
          padding: 4px 8px;
          text-align: center;
          font-size: 10px;
          font-weight: 600;
          letter-spacing: 0.12em;
          text-transform: uppercase;
        }
        .tag.keep { background: rgba(61, 124, 87, 0.13); color: var(--green); }
        .tag.add  { background: rgba(201, 169, 97, 0.16); color: #B89548; }
        .fund-name {
          min-width: 0;
          font-family: var(--font-display);
          font-size: 15px;
          color: var(--ink);
          line-height: 1.18;
        }
        .fund-name small {
          display: block;
          margin-top: 4px;
          color: var(--ink-soft);
          font-family: var(--font-body);
          font-size: 10px;
          letter-spacing: 0.06em;
          text-transform: uppercase;
        }
        .amount {
          color: #B89548;
          font-size: 13px;
          font-weight: 600;
          font-feature-settings: "tnum";
          white-space: nowrap;
        }
      `}</style>
    </section>
  );
}

function AllocationRing({
  equity,
  debt,
  gold,
  centerLabel,
}: {
  equity: number;
  debt: number;
  gold: number;
  centerLabel: string;
}) {
  // r=42, C = 2 * PI * 42 ≈ 263.89. Build proportional arcs by accumulating offsets.
  const C = 264;
  const eqLen = equity * C;
  const dbLen = debt * C;
  const glLen = gold * C;
  return (
    <svg viewBox="0 0 120 120" width="118" height="118" role="img" aria-label="Allocation ring">
      <circle cx="60" cy="60" r="42" fill="none" stroke="var(--cream-deep)" strokeWidth="16" />
      <g transform="rotate(-90 60 60)">
        <circle cx="60" cy="60" r="42" fill="none" stroke="var(--champagne)" strokeWidth="16"
                strokeDasharray={`${eqLen} ${C}`} strokeDashoffset="0" />
        <circle cx="60" cy="60" r="42" fill="none" stroke="var(--green)" strokeWidth="16"
                strokeDasharray={`${dbLen} ${C}`} strokeDashoffset={`${-eqLen}`} />
        <circle cx="60" cy="60" r="42" fill="none" stroke="var(--ink)" strokeWidth="16"
                strokeDasharray={`${glLen} ${C}`} strokeDashoffset={`${-(eqLen + dbLen)}`} />
      </g>
      <text x="60" y="58" textAnchor="middle"
            fontFamily="Fraunces" fontSize="14" fill="var(--ink)">
        {centerLabel}
      </text>
      <text x="60" y="72" textAnchor="middle"
            fontFamily="Inter" fontSize="8" letterSpacing="1" fill="var(--ink-soft)">
        MONTHLY
      </text>
    </svg>
  );
}

function LegendRow({
  swatch,
  label,
  value,
}: {
  swatch: "champagne" | "green" | "ink" | "soft";
  label: string;
  value: string;
}) {
  return (
    <div className="legend-row">
      <span>
        <i className={`legend-swatch swatch-${swatch}`} />
        {label}
      </span>
      <b>{value}</b>
      <style>{`
        .legend-row {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 8px 0;
          border-bottom: 1px solid var(--cream-deep);
          font-size: 12px;
          color: var(--ink-soft);
        }
        .legend-row:last-child { border-bottom: none; }
        .legend-row span { display: inline-flex; align-items: center; gap: 8px; }
        .legend-row b {
          color: var(--ink);
          font-family: var(--font-display);
          font-weight: 400;
          font-size: 13px;
        }
        .legend-swatch {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          display: inline-block;
        }
        .swatch-champagne { background: var(--champagne); }
        .swatch-green     { background: var(--green); }
        .swatch-ink       { background: var(--ink); }
        .swatch-soft      { background: var(--ink-soft); opacity: 0.45; }
      `}</style>
    </div>
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
