import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { ReactNode } from "react";

const mocks = vi.hoisted(() => ({
  connect: vi.fn<() => Promise<void>>(),
  disconnect: vi.fn<() => Promise<void>>(),
  createClient: vi.fn(),
}));

vi.mock("./pcClient", () => ({
  API_BASE: "",
  createClient: (mode: "fresh" | "resume" | "simulator" | "emergency") => {
    mocks.createClient(mode);
    return {
      connect: mocks.connect,
      disconnect: mocks.disconnect,
      sendText: vi.fn(),
    };
  },
}));

vi.mock("@pipecat-ai/client-react", () => ({
  PipecatClientProvider: ({ children }: { children: ReactNode }) => children,
  PipecatClientAudio: () => null,
  usePipecatClient: () => ({
    connect: mocks.connect,
    disconnect: mocks.disconnect,
    sendText: vi.fn(),
  }),
  usePipecatClientMediaTrack: () => null,
  useRTVIClientEvent: () => undefined,
}));

import App from "./App";

const memory = {
  available: true,
  user_id: "rakshit",
  user_name: "Rakshit",
  conversation_id: "conversation",
  last_conversation_at: "2026-07-26T05:00:00Z",
  headline: "Continue your home plan",
  summary: "You paused to confirm the home budget.",
  completed_plan: false,
  summary_status: "ready",
};

describe("App memory route", () => {
  beforeEach(() => {
    window.history.pushState({}, "", "/");
    mocks.connect.mockReset();
    mocks.disconnect.mockReset();
    mocks.createClient.mockClear();
    vi.unstubAllGlobals();
  });

  it("does not fetch memory on the fresh route", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    await waitFor(() => expect(screen.getByText("Maya is ready")).toBeInTheDocument());
    expect(fetchMock).not.toHaveBeenCalled();
    expect(mocks.createClient).toHaveBeenCalledWith("fresh");
  });

  it("starts the simulator route without fetching saved memory", async () => {
    window.history.pushState({}, "", "/simulator");
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    expect(await screen.findByText("Rehearse a decision before you make it")).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
    expect(mocks.createClient).toHaveBeenCalledWith("simulator");
    await userEvent.click(
      screen.getByRole("button", { name: "Start financial decision simulator with Maya" }),
    );
    expect(mocks.createClient).toHaveBeenLastCalledWith("simulator");
  });

  it("starts emergency mode from the simulator entry", async () => {
    window.history.pushState({}, "", "/simulator");
    vi.stubGlobal("fetch", vi.fn());

    render(<App />);

    await userEvent.click(
      screen.getByRole("button", { name: "Start emergency planning with Maya" }),
    );
    expect(mocks.createClient).toHaveBeenLastCalledWith("emergency");
  });

  it("loads memory once and renders the personalized card", async () => {
    window.history.pushState({}, "", "/memory");
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => memory,
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    expect(screen.getByText("Loading your last conversation")).toBeInTheDocument();
    expect(await screen.findByText("Continue your home plan")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledOnce();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/memory/latest?user_id=rakshit",
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    );
    expect(mocks.createClient).toHaveBeenCalledWith("resume");
  });

  it("falls back to a usable fresh card after a malformed response", async () => {
    window.history.pushState({}, "", "/memory");
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ available: true, headline: 42 }),
    }));

    render(<App />);

    expect(await screen.findByText("No previous plan found")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Start planning with Maya" })).toBeEnabled();
    await userEvent.click(screen.getByRole("button", { name: "Start planning with Maya" }));
    expect(mocks.createClient).toHaveBeenCalledWith("fresh");
  });

  it("falls back safely after a network error", async () => {
    window.history.pushState({}, "", "/memory");
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));

    render(<App />);

    expect(await screen.findByText("No previous plan found")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Start planning with Maya" })).toBeEnabled();
  });

  it("selects fresh mode when the user starts over", async () => {
    window.history.pushState({}, "", "/memory");
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: async () => memory,
    }));
    render(<App />);

    await screen.findByText("Continue your home plan");
    await userEvent.click(screen.getByRole("button", { name: "Start over with a fresh plan" }));

    expect(mocks.createClient).toHaveBeenCalledWith("fresh");
  });

  it("prevents repeated connection attempts while dialing", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", vi.fn());
    mocks.connect.mockImplementation(() => new Promise(() => undefined));
    render(<App />);

    await user.click(screen.getByRole("button", { name: "Start planning with Maya" }));
    const start = screen.getByRole("button", { name: "Start with Maya" });
    await user.dblClick(start);

    expect(mocks.connect).toHaveBeenCalledOnce();
    expect(screen.getByRole("button", { name: "Start call with Maya" })).toBeDisabled();
  });

  it("restores an actionable CTA after a connection error", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", vi.fn());
    mocks.connect.mockRejectedValue(new Error("mic denied"));
    mocks.disconnect.mockResolvedValue(undefined);
    render(<App />);

    await user.click(screen.getByRole("button", { name: "Start planning with Maya" }));
    await user.click(screen.getByRole("button", { name: "Start with Maya" }));

    expect(await screen.findByText(/Could not start call/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Start call with Maya" })).toBeEnabled();
  });
});
