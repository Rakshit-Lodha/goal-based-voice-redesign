import { useCallback, useMemo, useState } from "react";
import type { FormEvent } from "react";
import type { TransportState } from "@pipecat-ai/client-js";
import { PipecatClientProvider, PipecatClientAudio, usePipecatClient } from "@pipecat-ai/client-react";
import { API_BASE, createClient } from "./pcClient";
import PhoneFrame from "./components/PhoneFrame";
import BrandBar from "./components/BrandBar";
import Orb from "./components/Orb";
import Subtitle from "./components/Subtitle";
import MicAffordance from "./components/MicAffordance";
import Artifact from "./components/Artifact";
import OtpSheet, { type OtpRequest } from "./components/OtpSheet";
import LedgerPanel from "./components/LedgerPanel";
import PlanHero from "./screens/PlanHero";
import { useRtviEvent } from "./pcReact";
import { useMood, type Mood } from "./state/useMood";
import { usePause } from "./state/usePause";
import { useArtifactQueue } from "./state/artifactQueue";
import { useStateSnapshot } from "./state/useStateSnapshot";
import { toLedgerRows } from "./state/ledgerRows";
import type { OtpRequestEvent, ServerMessage } from "./types";

export default function App() {
  const client = useMemo(() => createClient(), []);

  return (
    // client-react's bundled .d.ts declares its own PipecatClient class, nominally
    // distinct from the one we construct though identical at runtime — cast here.
    <PipecatClientProvider client={client as never}>
      <PhoneFrame>
        <Conversation />
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
  const { active, queuedCount, dismiss } = useArtifactQueue();
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
  const mood: Mood = isPaused ? "paused" : baseMood;
  const live = transportState === "connected" || transportState === "ready";
  const micState = live ? "live" : dialing ? "connecting" : "idle";
  const isHero = active?.kind === "plan_hero";
  const hasSummonedSurface = !!active || !!otp;

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
    }
  });

  const startCall = useCallback(async () => {
    if (!client || dialing || live) return;
    setCallError(null);
    setDialing(true);
    try {
      await client.connect();
    } catch (error) {
      console.error("connect failed", error);
      setCallError("Could not start call. Check mic permission and backend :8001, then tap again.");
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

  const onRevise = useCallback((key: string) => {
    // Phase 7 only surfaces the intent — Phase 8 wires the synthetic user
    // input back to Pipecat so Maya picks it up conversationally.
    setLedgerOpen(false);
    console.info("[ledger.revise]", key);
  }, []);

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
        summoned={!isHero && hasSummonedSurface}
        corner={isHero}
      />
      {!isHero && <Subtitle mood={mood} />}
      {isHero ? (
        <PlanHero data={active.data as never} onDismiss={dismiss} />
      ) : (
        <Artifact artifact={active} queuedCount={queuedCount} onDismiss={dismiss} />
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
      {!isHero && (
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
