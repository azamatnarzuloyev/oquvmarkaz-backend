import json
import logging
import re
import asyncio
import requests as req_lib
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"


def _bot_token() -> str:
    return getattr(settings, "TELEGRAM_BOT_TOKEN", "")


def _send_message(chat_id: int, text: str, reply_markup=None) -> bool:
    token = _bot_token()
    if not token:
        return False
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    try:
        url = TELEGRAM_API.format(token=token, method="sendMessage")
        r = req_lib.post(url, json=payload, timeout=10)
        r.raise_for_status()
        return True
    except Exception as e:
        logger.error("Telegram xabar yuborishda xato: %s", e)
        return False


def _extract_phone(text: str) -> str | None:
    clean = re.sub(r"[\s\-\(\)]", "", text)
    pattern = r"(\+?998\d{9}|\b[89]\d{8}\b)"
    match = re.search(pattern, clean)
    if match:
        phone = re.sub(r"[^\d+]", "", match.group())
        if not phone.startswith("+"):
            phone = "+998" + phone[-9:]
        return phone
    return None


def _get_or_create_lead(telegram_id: int, full_name: str, phone: str, username: str):
    from apps.leads.models import Lead, LeadSource, LeadActivity, ActivityType
    from apps.integrations.models import TelegramActivity

    existing = Lead.objects.filter(phone=phone).first()
    if existing:
        TelegramActivity.objects.create(
            telegram_id=telegram_id,
            username=username,
            full_name=full_name,
            phone=phone,
            status=TelegramActivity.Status.DUPLICATE,
            lead=existing,
        )
        return existing, True

    lead = Lead.objects.create(
        full_name=full_name or f"Telegram: {telegram_id}",
        phone=phone,
        source=LeadSource.TELEGRAM,
        notes=f"Telegram bot orqali keldi. @{username}" if username else "Telegram bot orqali keldi.",
    )
    LeadActivity.objects.create(
        lead=lead,
        created_by=None,
        type=ActivityType.NOTE,
        content=f"Telegram bot orqali avtomatik yaratildi. ID: {telegram_id}",
    )
    TelegramActivity.objects.create(
        telegram_id=telegram_id,
        username=username,
        full_name=full_name,
        phone=phone,
        status=TelegramActivity.Status.LEAD_CREATED,
        lead=lead,
    )
    logger.info("Telegram lead yaratildi: %s (%s)", full_name, phone)
    return lead, False


def _handle_update(update: dict):
    message = update.get("message") or update.get("edited_message")
    if not message:
        return

    chat_id   = message["chat"]["id"]
    user      = message.get("from", {})
    username  = user.get("username", "")
    first     = user.get("first_name", "")
    last      = user.get("last_name", "")
    full_name = f"{first} {last}".strip()
    text      = message.get("text", "").strip()

    # /start buyrug'i
    if text in ("/start", "/start@" + _get_bot_username()):
        _send_message(
            chat_id,
            f"Salom, <b>{first}</b>! 👋\n\n"
            "O'quv markazimizga xush kelibsiz! 🎓\n\n"
            "Mutaxassisimiz siz bilan bog'lanishi uchun "
            "<b>telefon raqamingizni</b> yuboring.\n\n"
            "📱 Masalan: <code>+998 90 123 45 67</code>",
        )
        return

    # Telefon raqam kontakt orqali
    contact = message.get("contact")
    if contact:
        phone = contact.get("phone_number", "")
        if phone and not phone.startswith("+"):
            phone = "+" + phone
        if phone:
            lead, duplicate = _get_or_create_lead(chat_id, full_name, phone, username)
            if duplicate:
                _send_message(
                    chat_id,
                    f"✅ Siz allaqachon ro'yxatdan o'tgansiz!\n"
                    f"📞 Raqam: <code>{phone}</code>\n\n"
                    "Tez orada mutaxassisimiz bog'lanadi! 🎓",
                )
            else:
                _send_message(
                    chat_id,
                    f"✅ Rahmat! Raqamingiz qabul qilindi.\n"
                    f"📞 <code>{phone}</code>\n\n"
                    "Mutaxassisimiz tez orada siz bilan bog'lanadi! 🎓",
                )
        return

    # Matndan telefon raqam izlash
    phone = _extract_phone(text)
    if phone:
        lead, duplicate = _get_or_create_lead(chat_id, full_name, phone, username)
        if duplicate:
            _send_message(
                chat_id,
                f"✅ Bu raqam allaqachon tizimimizda bor!\n"
                f"📞 <code>{phone}</code>\n\n"
                "Mutaxassisimiz tez orada bog'lanadi! 🎓",
            )
        else:
            _send_message(
                chat_id,
                f"✅ Rahmat! Raqamingiz qabul qilindi.\n"
                f"📞 <code>{phone}</code>\n\n"
                "Mutaxassisimiz tez orada siz bilan bog'lanadi! 🎓",
            )
        return

    # Boshqa xabar
    from apps.integrations.models import TelegramActivity
    TelegramActivity.objects.create(
        telegram_id=telegram_id if (telegram_id := chat_id) else chat_id,
        username=username,
        full_name=full_name,
        message_text=text[:500],
        status=TelegramActivity.Status.WAITING,
    )
    _send_message(
        chat_id,
        "📱 Telefon raqamingizni yuboring.\n"
        "Masalan: <code>+998 90 123 45 67</code>",
    )


def _get_bot_username() -> str:
    token = _bot_token()
    if not token:
        return ""
    try:
        url = TELEGRAM_API.format(token=token, method="getMe")
        r = req_lib.get(url, timeout=5)
        return r.json().get("result", {}).get("username", "")
    except Exception:
        return ""


def setup_webhook(base_url: str) -> dict:
    """Telegram webhook URL ni o'rnatish."""
    token = _bot_token()
    if not token:
        return {"ok": False, "error": "TELEGRAM_BOT_TOKEN yo'q"}
    webhook_url = f"{base_url}/api/webhooks/telegram/"
    url = TELEGRAM_API.format(token=token, method="setWebhook")
    try:
        r = req_lib.post(url, json={"url": webhook_url, "drop_pending_updates": True}, timeout=10)
        return r.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}


def get_webhook_info() -> dict:
    token = _bot_token()
    if not token:
        return {"ok": False}
    try:
        url = TELEGRAM_API.format(token=token, method="getWebhookInfo")
        r = req_lib.get(url, timeout=5)
        return r.json()
    except Exception:
        return {"ok": False}


class TelegramWebhookView(APIView):
    """
    Telegram Bot webhook endpoint.
    POST — Telegram serverlaridan update qabul qilish
    """
    permission_classes = (AllowAny,)

    def post(self, request):
        try:
            update = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"ok": False}, status=400)

        try:
            _handle_update(update)
        except Exception as e:
            logger.error("Telegram update xatosi: %s", e, exc_info=True)

        return HttpResponse("OK", content_type="text/plain")
