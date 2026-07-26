import { describe, expect, it } from "vitest";

import { entryModeForPath, isMemoryCard } from "./memory";
import { offerUrlForMode } from "./pcClient";

const memory = {
  available: true,
  user_id: "rakshit",
  user_name: "Rakshit",
  conversation_id: "conversation",
  last_conversation_at: "2026-07-26T05:00:00Z",
  headline: "Continue your home plan",
  summary: "You paused before confirming the home budget.",
  completed_plan: false,
  summary_status: "fallback",
};

describe("memory route mode", () => {
  it.each([
    ["/", "fresh"],
    ["/memory", "resume"],
    ["/memory/", "resume"],
    ["/simulator", "simulator"],
    ["/simulator/", "simulator"],
    ["/unknown", "fresh"],
  ])("maps %s to %s", (path, expected) => {
    expect(entryModeForPath(path)).toBe(expected);
  });
});

describe("memory response validation", () => {
  it("accepts a complete display-safe response", () => {
    expect(isMemoryCard(memory)).toBe(true);
  });

  it("rejects unavailable and malformed responses", () => {
    expect(isMemoryCard({ available: false })).toBe(false);
    expect(isMemoryCard({ ...memory, summary: 42 })).toBe(false);
  });
});

describe("offer endpoint", () => {
  it("adds the selected memory mode to WebRTC signaling", () => {
    expect(offerUrlForMode("fresh")).toContain("memory_mode=fresh");
    expect(offerUrlForMode("resume")).toContain("memory_mode=resume");
    expect(offerUrlForMode("simulator")).toContain("memory_mode=simulator");
    expect(offerUrlForMode("emergency")).toContain("memory_mode=emergency");
  });
});
