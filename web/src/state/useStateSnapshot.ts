import { useState } from "react";
import { useRtviEvent } from "../pcReact";
import type { ServerMessage, Snapshot, StateEvent } from "../types";

function isStateEvent(message: unknown): message is StateEvent {
  return !!message && typeof message === "object" && (message as ServerMessage).type === "state";
}

/**
 * The latest live STATE snapshot from the backend.
 *
 * Mirrors core/session.py snapshot() — the same `payload` field the
 * artifact queue uses to detect last_event transitions for auto-dismiss.
 * Independent listener; React reconciles each hook subscription separately.
 */
export function useStateSnapshot(): Snapshot | null {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  useRtviEvent("serverMessage", (message) => {
    if (isStateEvent(message)) setSnapshot(message.payload);
  });
  return snapshot;
}
