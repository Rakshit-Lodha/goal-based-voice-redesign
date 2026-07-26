import type { ReactNode } from "react";
import type { ArtifactEvent } from "../types";
import {
  AaConsentSheet,
  EmergencyShockwaveCard,
  FamilyRecapCard,
  FundsPickerSheet,
  GoalsRecapCard,
  GoalTypesPickerCard,
  IncomeSnapshotCard,
  InflationCurveCard,
  InvestmentsCard,
  MfcConsentSheet,
  MfcReviewCard,
  RiskRevealCard,
  ScenarioComparisonCard,
  SimulatorMenuCard,
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
    case "mfc_review":
      return <MfcReviewCard data={event.data as never} />;
    case "aa_consent":
      return <AaConsentSheet data={event.data as never} />;
    case "income_snapshot":
      return <IncomeSnapshotCard data={event.data as never} />;
    case "investments_review":
      return <InvestmentsCard data={event.data as never} />;
    case "goal_types_picker":
      return <GoalTypesPickerCard data={event.data as never} />;
    case "simulator_menu":
      return <SimulatorMenuCard data={event.data as never} />;
    case "scenario_comparison":
      return <ScenarioComparisonCard data={event.data as never} />;
    case "emergency_shockwave":
      return <EmergencyShockwaveCard data={event.data as never} />;
    case "goals_recap":
      return <GoalsRecapCard data={event.data as never} />;
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
