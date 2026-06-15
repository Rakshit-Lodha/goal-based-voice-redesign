import { useCallback, useMemo, useRef, useState } from "react";
import { useRtviEvent } from "../pcReact";
import type { ArtifactEvent, ServerMessage, StateEvent } from "../types";

function isArtifactEvent(message: unknown): message is ArtifactEvent {
  return !!message && typeof message === "object" && (message as ServerMessage).type === "artifact";
}

function isConsent(kind: string): boolean {
  return kind.endsWith("_consent");
}

function isStateEvent(message: unknown): message is StateEvent {
  return !!message && typeof message === "object" && (message as ServerMessage).type === "state";
}

export function useArtifactQueue() {
  const [active, setActive] = useState<ArtifactEvent | null>(null);
  const [queue, setQueue] = useState<ArtifactEvent[]>([]);
  const activeRef = useRef<ArtifactEvent | null>(null);
  // The state-event tick that "anchors" the active artifact. The first state
  // event after an artifact is summoned sets this; any subsequent state event
  // (i.e. another tool call) advances the queue. Using tick instead of
  // last_event name correctly handles two consecutive calls to the same
  // tool (e.g. confirm_financial_snapshot for cashflow then for investments).
  const activeTickRef = useRef<number | null>(null);
  // Highest tick seen so far. When showNext promotes a queued artifact, we
  // anchor to this so the next tool call dismisses it immediately — otherwise
  // the queue would need two ticks per advance (anchor + dismiss).
  const latestTickRef = useRef<number | null>(null);

  const showNext = useCallback(() => {
    setQueue((items) => {
      const [next, ...rest] = items;
      activeRef.current = next ?? null;
      activeTickRef.current = next ? latestTickRef.current : null;
      setActive(next ?? null);
      return rest;
    });
  }, []);

  const dismiss = useCallback(() => {
    if (queue.length > 0) {
      showNext();
      return;
    }
    activeRef.current = null;
    activeTickRef.current = null;
    setActive(null);
  }, [queue.length, showNext]);

  useRtviEvent("serverMessage", (message) => {
    if (isStateEvent(message)) {
      const tick = message.payload.tick;
      if (typeof tick === "number") latestTickRef.current = tick;
      if (!activeRef.current || typeof tick !== "number") return;
      if (activeTickRef.current === null) {
        activeTickRef.current = tick;
        return;
      }
      if (tick !== activeTickRef.current) {
        dismiss();
      }
      return;
    }

    if (!isArtifactEvent(message)) return;

    console.info("[artifact]", message.kind, message.data);
    if (!activeRef.current) {
      activeRef.current = message;
      activeTickRef.current = null;
      setActive(message);
      return;
    }
    // Same kind arriving while still active = a live correction (e.g. user
    // edited income, AA re-pulled). Replace in place so the visible card
    // updates without sliding off and back on. activeTickRef stays so the
    // next-tick dismiss is still deterministic.
    if (activeRef.current.kind === message.kind) {
      activeRef.current = message;
      setActive(message);
      return;
    }
    // Consent → result handoff. The *_consent artifacts are emitted before a
    // tool blocks on the OTP wait; the matching result (mfc_review,
    // income_snapshot, …) is emitted from the *same* tool after the wait.
    // The next-different-tool dismiss can't help here because there is no
    // different tool — the result would otherwise queue behind the consent
    // and surface at the wrong moment. Replace in place.
    if (isConsent(activeRef.current.kind) && !isConsent(message.kind)) {
      activeRef.current = message;
      setActive(message);
      return;
    }
    setQueue((items) => [...items, message]);
  });

  return useMemo(() => ({ active, queuedCount: queue.length, dismiss }), [active, queue.length, dismiss]);
}
