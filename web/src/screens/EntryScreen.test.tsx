import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import EntryScreen from "./EntryScreen";
import type { MemoryCard } from "../memory";

const memory: MemoryCard = {
  available: true,
  user_id: "rakshit",
  user_name: "Rakshit",
  conversation_id: "conversation",
  last_conversation_at: "2026-07-26T05:00:00Z",
  headline: "Continue your home plan",
  summary: "You paused to discuss the home budget with your spouse.",
  completed_plan: false,
  summary_status: "ready",
};

describe("EntryScreen", () => {
  it("retains the fresh card", () => {
    render(
      <EntryScreen
        routeMode="fresh"
        memoryState={{ status: "idle" }}
        onStart={vi.fn()}
        onStartOver={vi.fn()}
      />,
    );

    expect(screen.getByText("Maya is ready")).toBeInTheDocument();
    expect(screen.getAllByText("Start planning").length).toBeGreaterThan(0);
    expect(screen.queryByText("Start over with a fresh plan")).not.toBeInTheDocument();
  });

  it("renders both simulator and emergency entry actions", async () => {
    const user = userEvent.setup();
    const onEmergency = vi.fn();
    render(
      <EntryScreen
        routeMode="simulator"
        memoryState={{ status: "idle" }}
        onStart={vi.fn()}
        onStartOver={vi.fn()}
        onEmergency={onEmergency}
      />,
    );

    expect(screen.getByText("Your financial picture is ready")).toBeInTheDocument();
    expect(screen.getByText("Rehearse a decision before you make it")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Start financial decision simulator with Maya" }),
    ).toBeEnabled();
    await user.click(
      screen.getByRole("button", { name: "Start emergency planning with Maya" }),
    );
    expect(onEmergency).toHaveBeenCalledOnce();
    expect(screen.queryByText("Start over with a fresh plan")).not.toBeInTheDocument();
  });

  it("shows a stable disabled loading card", () => {
    render(
      <EntryScreen
        routeMode="resume"
        memoryState={{ status: "loading" }}
        onStart={vi.fn()}
        onStartOver={vi.fn()}
      />,
    );

    expect(screen.getByText("Loading your last conversation")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Start planning with Maya" })).toBeDisabled();
  });

  it("renders personalized text and both accessible actions", async () => {
    const user = userEvent.setup();
    const onStart = vi.fn();
    const onStartOver = vi.fn();
    render(
      <EntryScreen
        routeMode="resume"
        memoryState={{ status: "available", memory }}
        onStart={onStart}
        onStartOver={onStartOver}
      />,
    );

    expect(screen.getByText("Maya remembers")).toBeInTheDocument();
    expect(screen.getByText("Welcome back, Rakshit")).toBeInTheDocument();
    expect(screen.getByText("Continue your home plan")).toBeInTheDocument();
    expect(screen.getByText(memory.summary)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Resume planning with Maya" }));
    await user.click(screen.getByRole("button", { name: "Start over with a fresh plan" }));
    expect(onStart).toHaveBeenCalledOnce();
    expect(onStartOver).toHaveBeenCalledOnce();
  });

  it("forces review copy for a completed plan and ignores extra sensitive fields", () => {
    const responseWithExtraData = {
      ...memory,
      completed_plan: true,
      headline: "Close the old plan",
      income: 150000,
    };
    render(
      <EntryScreen
        routeMode="resume"
        memoryState={{ status: "available", memory: responseWithExtraData }}
        onStart={vi.fn()}
        onStartOver={vi.fn()}
      />,
    );

    expect(screen.getByText("Review or update your wealth plan")).toBeInTheDocument();
    expect(screen.queryByText("150000")).not.toBeInTheDocument();
  });

  it("falls back to the fresh card when no memory is available", () => {
    render(
      <EntryScreen
        routeMode="resume"
        memoryState={{ status: "unavailable" }}
        onStart={vi.fn()}
        onStartOver={vi.fn()}
      />,
    );

    expect(screen.getByText("No previous plan found")).toBeInTheDocument();
    expect(screen.getByText("Start your guided wealth plan")).toBeInTheDocument();
  });
});
