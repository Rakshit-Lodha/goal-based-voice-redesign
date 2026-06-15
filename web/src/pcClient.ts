import { PipecatClient } from "@pipecat-ai/client-js";
import { SmallWebRTCTransport } from "@pipecat-ai/small-webrtc-transport";

// The FastAPI backend (server.py). In the redesign worktree Vite proxies /api to :8001.
export const API_BASE = import.meta.env.VITE_API_BASE ?? "";
export const OFFER_URL = import.meta.env.VITE_OFFER_URL ?? `${API_BASE}/api/offer`;

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

export function createClient(): PipecatClient {
  const transport = new SmallWebRTCTransport({
    webrtcRequestParams: { endpoint: OFFER_URL },
    iceServers: iceServers(),
  });
  return new PipecatClient({ transport, enableMic: true, enableCam: false });
}
