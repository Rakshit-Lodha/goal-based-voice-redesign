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
  const activeToolRef = useRef<string | null>(null);

  const showNext = useCallback(() => {
    setQueue((items) => {
      const [next, ...rest] = items;
      activeRef.current = next ?? null;
      activeToolRef.current = null;
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
    activeToolRef.current = null;
    setActive(null);
  }, [queue.length, showNext]);

  useRtviEvent("serverMessage", (message) => {
    if (isStateEvent(message)) {
      const lastEvent = message.payload.last_event;
      if (!activeRef.current || !lastEvent) return;
      if (!activeToolRef.current) {
        activeToolRef.current = lastEvent;
        return;
      }
      if (activeToolRef.current !== lastEvent) {
        dismiss();
      }
      return;
    }

    if (!isArtifactEvent(message)) return;

    console.info("[artifact]", message.kind, message.data);
    if (!activeRef.current) {
      activeRef.current = message;
      activeToolRef.current = null;
      setActive(message);
      return;
    }
    // Same kind arriving while still active = a live correction (e.g. user
    // edited income, AA re-pulled). Replace in place so the visible card
    // updates without sliding off and back on. activeToolRef stays so the
    // next-different-tool dismiss is still deterministic.
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
