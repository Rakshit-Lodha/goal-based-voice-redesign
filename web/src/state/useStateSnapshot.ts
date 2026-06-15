import { useState } from "react";
import { useRtviEvent } from "../pcReact";
import type { ServerMessage, Snapshot, StateEvent } from "../types";

// Module-level cache so a component mounted between two state events sees
// the most recent snapshot immediately. Without this, late mounters (e.g.
// InvestmentsCard surfacing after pull_account_aggregator's state event has
// already flowed past) stay null until the next tool call fires a state.
let latestSnapshot: Snapshot | null = null;

function isStateEvent(message: unknown): message is StateEvent {
  return !!message && typeof message === "object" && (message as ServerMessage).type === "state";
}

/**
 * The latest live STATE snapshot from the backend.
 *
 * Mirrors core/session.py snapshot() — the same `payload` field the
 * artifact queue uses to detect last_event transitions for auto-dismiss.
 */
export function useStateSnapshot(): Snapshot | null {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(latestSnapshot);
  useRtviEvent("serverMessage", (message) => {
    if (isStateEvent(message)) {
      latestSnapshot = message.payload;
      setSnapshot(message.payload);
    }
  });
  return snapshot;
}
