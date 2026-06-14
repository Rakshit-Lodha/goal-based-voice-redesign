import type { Snapshot } from "../types";

/**
 * One confirmed fact in the ledger. `reviseKey` is the conversational
 * handle Maya recognises when Phase 8 wires the synthetic user input
 * ("I want to update my <reviseKey>"). Keep keys natural-language.
 */
export interface LedgerRow {
  id: string;
  title: string;
  value: string;
  reviseKey: string;
}

function lakhs(n: number): string {
  if (n >= 10_000_000) return `₹${(n / 10_000_000).toFixed(1)} cr`;
  if (n >= 100_000) return `₹${(n / 100_000).toFixed(1)} L`;
  if (n >= 1_000) return `₹${(n / 1_000).toFixed(0)}k`;
  return `₹${Math.round(n).toLocaleString("en-IN")}`;
}

function monthly(n: number): string {
  return `${lakhs(n)}/mo`;
}

/**
 * Project the snapshot to the rows we surface in the ledger panel.
 * Order matches the locked 9-stage Maya flow: risk → family → MFC → AA
 * → manual assets → goals → SIP plan. Rows only appear when their
 * underlying STATE field is genuinely populated.
 */
export function toLedgerRows(snapshot: Snapshot | null): LedgerRow[] {
  if (!snapshot) return [];
  const rows: LedgerRow[] = [];

  if (snapshot.risk_profile) {
    rows.push({
      id: "risk",
      title: "Risk profile",
      value: snapshot.risk_profile,
      reviseKey: "risk profile",
    });
  }

  if (snapshot.family) {
    const { spouse_age, children, dependents_count } = snapshot.family;
    const parts: string[] = [];
    if (spouse_age != null) parts.push(`spouse ${spouse_age}`);
    if (children?.length) {
      parts.push(`${children.length} ${children.length === 1 ? "child" : "children"}`);
    }
    rows.push({
      id: "family",
      title: "Family",
      value: parts.join(" · ") || `${dependents_count} dependents`,
      reviseKey: "family",
    });
  }

  if (snapshot.portfolio && (snapshot.portfolio.total_value > 0 || snapshot.portfolio.holdings.length > 0)) {
    rows.push({
      id: "portfolio",
      title: "Mutual fund portfolio",
      value: lakhs(snapshot.portfolio.total_value),
      reviseKey: "mutual fund holdings",
    });
  }

  if (snapshot.monthly_income != null) {
    const income = snapshot.monthly_income;
    const expense = snapshot.monthly_expenses ?? 0;
    rows.push({
      id: "cashflow",
      title: "Cash flow",
      value: `${monthly(income)} in · ${monthly(expense)} out`,
      reviseKey: "income and expenses",
    });
  }

  if (snapshot.aa_assets) {
    const { epf, nps, stocks } = snapshot.aa_assets;
    rows.push({
      id: "aa_assets",
      title: "EPF · NPS · stocks",
      value: `${lakhs(epf)} · ${lakhs(nps)} · ${lakhs(stocks)}`,
      reviseKey: "EPF NPS or stocks",
    });
  }

  for (const asset of snapshot.additional_assets ?? []) {
    rows.push({
      id: `asset-${asset.name}`,
      title: asset.name,
      value: lakhs(asset.value),
      reviseKey: asset.name,
    });
  }

  for (const goal of snapshot.goals ?? []) {
    rows.push({
      id: `goal-${goal.name}`,
      title: goal.name,
      value: `${lakhs(goal.target_amount_today)} · ${goal.horizon_years}y`,
      reviseKey: goal.name,
    });
  }

  if (snapshot.portfolio?.total_monthly_sip || snapshot.plan_pdf_url) {
    const sip = snapshot.portfolio?.total_monthly_sip ?? 0;
    rows.push({
      id: "sip-plan",
      title: "Monthly SIP plan",
      value: sip > 0 ? monthly(sip) : "Plan ready",
      reviseKey: "SIP plan",
    });
  }

  return rows;
}
