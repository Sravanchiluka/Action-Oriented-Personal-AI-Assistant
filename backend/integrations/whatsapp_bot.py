import asyncio
from html import escape

from fastapi import APIRouter, Request
from fastapi.responses import Response

from ai_engine import fast_command_handler, process_message

try:
    from twilio.twiml.messaging_response import MessagingResponse
except Exception:
    MessagingResponse = None

router = APIRouter()


def _build_twiml(message):
    if MessagingResponse is not None:
        response = MessagingResponse()
        response.message(message)
        return str(response)

    safe_message = escape(message or "")
    return f"<Response><Message>{safe_message}</Message></Response>"


@router.post("/whatsapp")
async def whatsapp_webhook(request: Request):
    data = await request.form()
    sender = (data.get("From") or "").strip()
    user_message = (data.get("Body") or "").strip()
    print(f"Incoming WhatsApp from {sender or 'unknown'}: {user_message}")

    if not user_message:
        reply = "Please send a message so I can help."
    else:
        fast_reply = await asyncio.to_thread(fast_command_handler, user_message)
        reply = fast_reply if fast_reply is not None else await asyncio.to_thread(process_message, user_message)

    print(f"WhatsApp reply: {reply}")

    return Response(
        content=_build_twiml(reply),
        media_type="application/xml",
        headers={"Cache-Control": "no-store"},
    )
