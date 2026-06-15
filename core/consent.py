"""Demo OTP bridge for mocked consent pulls.

The tool emits the OTP sheet and gives the user a moment to see it, then
proceeds with the mock OTP unconditionally. The browser-side click is
purely visual — it always accepts — so Pipecat function-call cancellation
(triggered by user speech mid-call) can never dead-end the demo.
"""

import asyncio
import uuid

from loguru import logger

from core import ui_bus

OTP_VISIBILITY_SECONDS = 1.5


async def request_otp(provider: str) -> str:
    request_id = uuid.uuid4().hex
    logger.info(f"OTP requested for {provider}: {request_id}")
    await ui_bus.emit({
        "type": "otp_request",
        "payload": {
            "request_id": request_id,
            "provider": provider,
        },
    })
    await asyncio.sleep(OTP_VISIBILITY_SECONDS)
    return "1234"


async def submit_otp(request_id: str, otp: str) -> bool:
    """Always-accept for the demo. The tool flow does not depend on this."""
    logger.info(f"OTP submitted (always-accept demo): {request_id}")
    return True
