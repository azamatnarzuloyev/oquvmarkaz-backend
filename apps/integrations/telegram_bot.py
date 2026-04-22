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

SYSTEM_PROMPT = """Siz "O'quv Markazi" ning Telegram boti — virtual yordamchisisiz.

QOIDALAR (qat'iy bajaring):
1. FAQAT o'quv markazi mavzularida gapiring: kurslar, narxlar, dars jadvali, o'qituvchilar, ro'yxatdan o'tish, sinov darsi.
2. Siyosat, din, sport, yangiliklar, shaxsiy maslahat — HECH QANDAY javob bermang.
3. Begona mavzuda savol bo'lsa: "Men faqat o'quv markazi haqida yordam bera olaman 😊" deying.
4. Hech qachon narx, chegirma yoki kafolat va'da qilmang — bular uchun mutaxassisga yo'naltiring.
5. Javob 2-3 gapdan oshmasin. O'zbek tilida. Emoji ishlating (1-2 ta).
6. Agar foydalanuvchi telefon raqam bermasa — har doim so'rang."""


def _get_ai_response(user_message: str) -> str | None:
    """OpenAI orqali mavzu cheklangan AI javob."""
    api_key = getattr(settings, "OPENAI_API_KEY", "")
    if not api_key:
        return None
    try:
        resp = req_lib.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": user_message},
                ],
                "max_tokens": 150,
                "temperature": 0.5,
            },
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.error("OpenAI Telegram xato: %s", e)
        return None


def _bot_token() -> str:
    return getattr(settings, "TELEGRAM_BOT_TOKEN", "")


PHONE_KEYBOARD = {
    "keyboard": [[{"text": "📱 Telefon raqamimni ulashish", "request_contact": True}]],
    "resize_keyboard": True,
    "one_time_keyboard": True,
}

REMOVE_KEYBOARD = {"remove_keyboard": True}


def _send_message(chat_id: int, text: str, reply_markup=None) -> bool:
    token = _bot_token()
    if not token:
        return False
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup is not None:
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
    if text.startswith("/start"):
        _send_message(
            chat_id,
            f"Salom, <b>{first}</b>! 👋\n\n"
            "O'quv markazimizga xush kelibsiz! 🎓\n\n"
            "Mutaxassisimiz siz bilan bog'lanishi uchun "
            "<b>telefon raqamingizni</b> ulashing 👇",
            reply_markup=PHONE_KEYBOARD,
        )
        return

    # Telefon raqam kontakt orqali (tugma bosilganda)
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
                    reply_markup=REMOVE_KEYBOARD,
                )
            else:
                _send_message(
                    chat_id,
                    f"✅ Rahmat! Raqamingiz qabul qilindi.\n"
                    f"📞 <code>{phone}</code>\n\n"
                    "Mutaxassisimiz tez orada siz bilan bog'lanadi! 🎓",
                    reply_markup=REMOVE_KEYBOARD,
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
                reply_markup=REMOVE_KEYBOARD,
            )
        else:
            _send_message(
                chat_id,
                f"✅ Rahmat! Raqamingiz qabul qilindi.\n"
                f"📞 <code>{phone}</code>\n\n"
                "Mutaxassisimiz tez orada siz bilan bog'lanadi! 🎓",
                reply_markup=REMOVE_KEYBOARD,
            )
        return

    # Boshqa xabar — AI javob (mavzu cheklangan)
    from apps.integrations.models import TelegramActivity
    TelegramActivity.objects.create(
        telegram_id=chat_id,
        username=username,
        full_name=full_name,
        message_text=text[:500],
        status=TelegramActivity.Status.WAITING,
    )
    ai_reply = _get_ai_response(text)
    reply_text = ai_reply or "📱 Telefon raqamingizni ulashing 👇"
    _send_message(chat_id, reply_text, reply_markup=PHONE_KEYBOARD)


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
