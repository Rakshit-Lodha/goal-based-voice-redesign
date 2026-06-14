import { useCallback, useMemo, useRef, useState } from "react";
import { useRtviEvent } from "../pcReact";
import type { ArtifactEvent, ServerMessage, StateEvent } from "../types";

function isArtifactEvent(message: unknown): message is ArtifactEvent {
  return !!message && typeof message === "object" && (message as ServerMessage).type === "artifact";
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
    setQueue((items) => [...items, message]);
  });

  return useMemo(() => ({ active, queuedCount: queue.length, dismiss }), [active, queue.length, dismiss]);
}
