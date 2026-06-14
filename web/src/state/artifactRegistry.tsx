import type { ReactNode } from "react";
import type { ArtifactEvent } from "../types";
import {
  AaConsentSheet,
  FamilyRecapCard,
  FundsPickerSheet,
  IncomeSnapshotCard,
  InflationCurveCard,
  InvestmentsCard,
  MfcConsentSheet,
  RatiosCard,
  RiskRevealCard,
  SipPlanFallback,
  SipSplitCard,
} from "../components/artifacts/Cards";

export function renderArtifact(event: ArtifactEvent): ReactNode {
  switch (event.kind) {
    case "risk_reveal":
      return <RiskRevealCard data={event.data as never} />;
    case "family_recap":
      return <FamilyRecapCard data={event.data as never} />;
    case "mfc_consent":
      return <MfcConsentSheet data={event.data as never} />;
    case "aa_consent":
      return <AaConsentSheet data={event.data as never} />;
    case "income_snapshot":
      return <IncomeSnapshotCard data={event.data as never} />;
    case "ratios":
      return <RatiosCard data={event.data as never} />;
    case "investments_review":
      return <InvestmentsCard data={event.data as never} />;
    case "inflation_curve":
      return <InflationCurveCard data={event.data as never} />;
    case "sip_split":
      return <SipSplitCard data={event.data as never} />;
    case "funds_picker":
      return <FundsPickerSheet data={event.data as never} />;
    case "plan_hero":
      return <SipPlanFallback data={event.data as { total_monthly_sip?: number }} />;
    default:
      return null;
  }
}
