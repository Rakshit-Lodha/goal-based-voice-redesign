import type { MemoryMode } from "./pcClient";

export type MemoryCard = {
  available: true;
  user_id: string;
  user_name: string;
  conversation_id: string;
  last_conversation_at: string;
  headline: string;
  summary: string;
  completed_plan: boolean;
  summary_status: "pending" | "ready" | "fallback" | "failed";
};

export type MemoryLoadState =
  | { status: "idle" | "loading" | "unavailable" }
  | { status: "available"; memory: MemoryCard };

export function entryModeForPath(pathname: string): MemoryMode {
  if (pathname === "/memory" || pathname === "/memory/") return "resume";
  if (pathname === "/simulator" || pathname === "/simulator/") return "simulator";
  return "fresh";
}

export function isMemoryCard(value: unknown): value is MemoryCard {
  if (!value || typeof value !== "object") return false;
  const card = value as Record<string, unknown>;
  return card.available === true
    && typeof card.user_id === "string"
    && typeof card.user_name === "string"
    && typeof card.conversation_id === "string"
    && typeof card.last_conversation_at === "string"
    && typeof card.headline === "string"
    && typeof card.summary === "string"
    && typeof card.completed_plan === "boolean"
    && ["pending", "ready", "fallback", "failed"].includes(String(card.summary_status));
}
