import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { FormEvent } from "react";
import type { TransportState } from "@pipecat-ai/client-js";
import { PipecatClientProvider, PipecatClientAudio, usePipecatClient } from "@pipecat-ai/client-react";
import { API_BASE, createClient, type MemoryMode } from "./pcClient";
import PhoneFrame from "./components/PhoneFrame";
import BrandBar from "./components/BrandBar";
import Orb from "./components/Orb";
import Subtitle from "./components/Subtitle";
import MicAffordance from "./components/MicAffordance";
import Artifact from "./components/Artifact";
import OtpSheet, { type OtpRequest } from "./components/OtpSheet";
import LedgerPanel from "./components/LedgerPanel";
import CascadeToast, { type CascadeDiff } from "./components/CascadeToast";
import PlanHero from "./screens/PlanHero";
import EntryScreen from "./screens/EntryScreen";
import IntroScreen from "./screens/IntroScreen";
import { useRtviEvent } from "./pcReact";
import { useMood, type Mood } from "./state/useMood";
import { usePause } from "./state/usePause";
import { useArtifactQueue } from "./state/artifactQueue";
import { useStateSnapshot } from "./state/useStateSnapshot";
import { toLedgerRows } from "./state/ledgerRows";
import type { CascadeDiffEvent, OtpRequestEvent, ServerMessage } from "./types";
import {
  entryModeForPath,
  isMemoryCard,
  type MemoryLoadState,
} from "./memory";

const DEMO_USER_ID = "rakshit";

export default function App() {
  const entryMode = entryModeForPath(window.location.pathname);
  const [memoryState, setMemoryState] = useState<MemoryLoadState>(
    entryMode === "resume" ? { status: "loading" } : { status: "idle" },
  );
  const [callMode, setCallMode] = useState<MemoryMode>(entryMode);
  const client = useMemo(() => createClient(callMode), [callMode]);
  const [entered, setEntered] = useState(false);

  useEffect(() => {
    if (entryMode !== "resume") return;
    const controller = new AbortController();
    void fetch(`${API_BASE}/api/memory/latest?user_id=${DEMO_USER_ID}`, {
      signal: controller.signal,
    })
      .then(async (response) => {
        if (!response.ok) throw new Error(`Memory request failed: ${response.status}`);
        const body: unknown = await response.json();
        setMemoryState(isMemoryCard(body)
          ? { status: "available", memory: body }
          : { status: "unavailable" });
      })
      .catch((error) => {
        if ((error as Error).name !== "AbortError") {
          console.warn("Could not load saved memory; using fresh mode", error);
          setMemoryState({ status: "unavailable" });
        }
      });
    return () => controller.abort();
  }, [entryMode]);

  const enterConversation = useCallback((mode: MemoryMode) => {
    setCallMode(mode);
    setEntered(true);
  }, []);

  return (
    // client-react's bundled .d.ts declares its own PipecatClient class, nominally
    // distinct from the one we construct though identical at runtime — cast here.
    <PipecatClientProvider client={client as never}>
      <PhoneFrame>
        {entered ? (
          <Conversation />
        ) : (
          <EntryScreen
            routeMode={entryMode}
            memoryState={memoryState}
            onStart={() => enterConversation(
              entryMode === "simulator"
                ? "simulator"
                : memoryState.status === "available"
                  ? "resume"
                  : "fresh",
            )}
            onStartOver={() => enterConversation("fresh")}
            onEmergency={() => enterConversation("emergency")}
          />
        )}
      </PhoneFrame>
      {/* Plays Maya's TTS audio coming back from the bot. */}
      <PipecatClientAudio />
    </PipecatClientProvider>
  );
}

/**
 * The conversation shell: brand bar (top), orb (centre, tap-to-pause),
 * subtitle (just below orb), mic affordance (bottom).
 *
 * Phase 4–7 will surface artifacts above the mic affordance and replace
 * the ledger chip placeholder with the live STATE-driven version.
 */
function Conversation() {
  const client = usePipecatClient();
  const baseMood = useMood();
  const { isPaused, togglePause } = usePause();
  const { active, dismiss } = useArtifactQueue();
  const snapshot = useStateSnapshot();
  const ledgerRows = useMemo(() => toLedgerRows(snapshot), [snapshot]);
  const [ledgerOpen, setLedgerOpen] = useState(false);
  const [transportState, setTransportState] = useState<TransportState>("disconnected");
  const [dialing, setDialing] = useState(false);
  const [callError, setCallError] = useState<string | null>(null);
  const [otp, setOtp] = useState<OtpRequest | null>(null);
  const [otpValue, setOtpValue] = useState("");
  const [otpError, setOtpError] = useState<string | null>(null);
  const [otpSubmitting, setOtpSubmitting] = useState(false);
  const [cascade, setCascade] = useState<CascadeDiff | null>(null);
  const cascadeTimerRef = useRef<number | null>(null);
  const mood: Mood = isPaused ? "paused" : baseMood;
  const live = transportState === "connected" || transportState === "ready";
  const micState = live ? "live" : dialing ? "connecting" : "idle";
  const isHero = active?.kind === "plan_hero";
  const hasSummonedSurface = !!active || !!otp;
  const showIntro = !live && !dialing && !active && !otp && !callError;

  useRtviEvent("transportStateChanged", (state) => {
    const nextState = state as TransportState;
    setTransportState(nextState);
    if (nextState === "connected" || nextState === "ready") {
      setDialing(false);
      setCallError(null);
    }
    if (nextState === "disconnected" || nextState === "error") {
      setDialing(false);
    }
  });

  useRtviEvent("serverMessage", (data) => {
    const msg = data as ServerMessage;
    if (isOtpRequest(msg)) {
      dismiss();
      setOtp(msg.payload);
      setOtpValue("");
      setOtpError(null);
      setOtpSubmitting(false);
      return;
    }
    if (isCascadeDiff(msg)) {
      if (cascadeTimerRef.current !== null) window.clearTimeout(cascadeTimerRef.current);
      setCascade({ label: msg.label, before: msg.before, after: msg.after });
      cascadeTimerRef.current = window.setTimeout(() => setCascade(null), 3500);
    }
  });

  useEffect(() => () => {
    if (cascadeTimerRef.current !== null) window.clearTimeout(cascadeTimerRef.current);
  }, []);

  const startCall = useCallback(async () => {
    if (!client || dialing || live) return;
    setCallError(null);
    setDialing(true);
    try {
      await client.connect();
    } catch (error) {
      console.error("connect failed", error);
      setCallError("Could not start call. Check mic permission and backend :8000, then tap again.");
      await client.disconnect().catch(() => undefined);
      setDialing(false);
    }
  }, [client, dialing, live]);

  const endCall = useCallback(async () => {
    setDialing(false);
    setCallError(null);
    setOtp(null);
    await client?.disconnect();
  }, [client]);

  const onRevise = useCallback(async (key: string) => {
    setLedgerOpen(false);
    if (!live || !client) return;
    try {
      await client.sendText(`I want to update my ${key}.`, {
        run_immediately: true,
        audio_response: true,
      });
    } catch (error) {
      console.error("[ledger.revise] sendText failed", error);
    }
  }, [client, live]);

  const submitOtp = useCallback(async (event: FormEvent) => {
    event.preventDefault();
    if (!otp) return;
    setOtpSubmitting(true);
    setOtpError(null);
    try {
      const response = await fetch(`${API_BASE}/api/otp`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ request_id: otp.request_id, otp: otpValue }),
      });
      const body = await response.json();
      if (!body.accepted) {
        setOtpError("This OTP request is no longer active. Ask Maya to trigger it again.");
        return;
      }
      setOtp(null);
      setOtpValue("");
    } catch (error) {
      setOtpError(`Could not verify OTP: ${String(error)}`);
    } finally {
      setOtpSubmitting(false);
    }
  }, [otp, otpValue]);

  return (
    <>
      <BrandBar ledgerCount={ledgerRows.length} onLedgerOpen={() => setLedgerOpen(true)} />
      <Orb
        mood={mood}
        onTap={togglePause}
        summoned={hasSummonedSurface}
        corner={false}
      />
      {!isHero && !showIntro && <Subtitle mood={mood} />}
      {showIntro ? (
        <IntroScreen onStart={startCall} dialing={dialing} />
      ) : isHero ? (
        <PlanHero data={active.data as never} onDismiss={dismiss} />
      ) : (
        <Artifact artifact={active} onDismiss={dismiss} />
      )}
      <OtpSheet
        otp={otp}
        value={otpValue}
        error={otpError}
        submitting={otpSubmitting}
        onChange={setOtpValue}
        onSubmit={submitOtp}
      />
      <LedgerPanel
        rows={ledgerRows}
        isOpen={ledgerOpen}
        onClose={() => setLedgerOpen(false)}
        onRevise={onRevise}
      />
      {cascade && <CascadeToast diff={cascade} />}
      {!isHero && !showIntro && (
        <MicAffordance
          state={micState}
          onStart={startCall}
          onEnd={endCall}
          error={callError}
        />
      )}
    </>
  );
}

function isOtpRequest(message: ServerMessage): message is OtpRequestEvent {
  return message.type === "otp_request" && !!message.payload;
}

function isCascadeDiff(message: ServerMessage): message is CascadeDiffEvent {
  return message.type === "cascade_diff"
    && typeof (message as CascadeDiffEvent).before === "number"
    && typeof (message as CascadeDiffEvent).after === "number";
}
