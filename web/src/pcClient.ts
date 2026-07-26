import { PipecatClient } from "@pipecat-ai/client-js";
import { SmallWebRTCTransport } from "@pipecat-ai/small-webrtc-transport";

// The FastAPI backend (server.py). Vite proxies local API traffic to :8000.
export const API_BASE = import.meta.env.VITE_API_BASE ?? "";
export const OFFER_URL = import.meta.env.VITE_OFFER_URL ?? `${API_BASE}/api/offer`;
export type MemoryMode = "fresh" | "resume" | "simulator" | "emergency";

export function offerUrlForMode(mode: MemoryMode): string {
  const separator = OFFER_URL.includes("?") ? "&" : "?";
  return `${OFFER_URL}${separator}memory_mode=${mode}`;
}

function iceServers(): RTCIceServer[] {
  const configured = import.meta.env.VITE_ICE_SERVERS;
  if (configured) {
    try {
      return JSON.parse(configured) as RTCIceServer[];
    } catch (error) {
      console.warn("Invalid VITE_ICE_SERVERS JSON; falling back to public STUN", error);
    }
  }
  return [{ urls: "stun:stun.l.google.com:19302" }];
}

export function createClient(memoryMode: MemoryMode = "fresh"): PipecatClient {
  const transport = new SmallWebRTCTransport({
    // The installed transport reuses this exact endpoint for POST and trickle
    // ICE PATCH, so the mode remains attached throughout signaling.
    webrtcRequestParams: { endpoint: offerUrlForMode(memoryMode) },
    iceServers: iceServers(),
  });
  return new PipecatClient({ transport, enableMic: true, enableCam: false });
}
