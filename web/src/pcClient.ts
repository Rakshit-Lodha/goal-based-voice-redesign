import { PipecatClient } from "@pipecat-ai/client-js";
import { SmallWebRTCTransport } from "@pipecat-ai/small-webrtc-transport";

// The FastAPI backend (server.py). In the redesign worktree Vite proxies /api to :8001.
export const API_BASE = import.meta.env.VITE_API_BASE ?? "";
export const OFFER_URL = import.meta.env.VITE_OFFER_URL ?? `${API_BASE}/api/offer`;

export function createClient(): PipecatClient {
  const transport = new SmallWebRTCTransport({
    webrtcRequestParams: { endpoint: OFFER_URL },
  });
  return new PipecatClient({ transport, enableMic: true, enableCam: false });
}
