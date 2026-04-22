import hashlib
import hmac
import json
import logging
import re
import requests
from django.conf import settings
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

logger = logging.getLogger(__name__)

GRAPH_URL = "https://graph.instagram.com/v21.0"


def _verify_signature(request) -> bool:
    """Meta webhook imzosini tekshirish."""
    signature = request.headers.get("X-Hub-Signature-256", "")
    if not signature.startswith("sha256="):
        return False
    secret = settings.INSTAGRAM_APP_SECRET.encode()
    expected = "sha256=" + hmac.new(secret, request.body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected)


def _send_dm(recipient_id: str, text: str, access_token: str) -> bool:
    """Instagram Direct Message yuborish."""
    url = f"{GRAPH_URL}/me/messages"
    payload = {
        "recipient": {"id": recipient_id},
        "message":   {"text": text},
        "access_token": access_token,
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        return True
    except Exception as e:
        logger.error("DM yuborishda xato: %s", e)
        return False


def _reply_comment(comment_id: str, text: str, access_token: str) -> bool:
    """Comment ga javob berish."""
    url = f"{GRAPH_URL}/{comment_id}/replies"
    try:
        resp = requests.post(url, data={"message": text, "access_token": access_token}, timeout=10)
        resp.raise_for_status()
        return True
    except Exception as e:
        logger.error("Comment javobida xato: %s", e)
        return False


def _get_ai_reply(comment_text: str) -> str:
    """Gemini API orqali AI javob generatsiya qilish."""
    api_key = getattr(settings, "GEMINI_API_KEY", None)
    if not api_key:
        return _default_reply()

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    prompt = f"""Siz o'quv markazining virtual yordamchisisiz.
Foydalanuvchi Instagram postiga shunday izoh qoldirdi: "{comment_text}"

Qisqa, do'stona va professional javob yozing (2-3 gap).
O'zbek tilida. Ularga DM (xabar) yuborishni so'rang va telefon raqamlarini so'rang."""

    try:
        resp = requests.post(
            url,
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        logger.error("Gemini API xato: %s", e)
        return _default_reply()


def _default_reply() -> str:
    return (
        "Salom! 😊 Izohingiz uchun rahmat! "
        "Batafsil ma'lumot olish uchun DM ga yozing yoki "
        "telefon raqamingizni yuboring — siz bilan bog'lanamiz! 📚"
    )


def _extract_phone(text: str) -> str | None:
    """Matndan telefon raqamini ajratib olish."""
    pattern = r"(\+?998\s?[\s\-]?\d{2}[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}|\b\d{9}\b)"
    match = re.search(pattern, text.replace(" ", ""))
    if match:
        phone = re.sub(r"[^\d+]", "", match.group())
        if not phone.startswith("+"):
            phone = "+998" + phone[-9:]
        return phone
    return None


def _create_lead_from_instagram(sender_id: str, sender_name: str, phone: str, message: str):
    """Instagram DM dan lead yaratish."""
    from apps.leads.models import Lead, LeadSource, LeadActivity, ActivityType

    existing = Lead.objects.filter(phone=phone).first()
    if existing:
        logger.info("Lead allaqachon mavjud: %s", phone)
        return existing

    lead = Lead.objects.create(
        full_name=sender_name or f"Instagram: {sender_id}",
        phone=phone,
        source=LeadSource.INSTAGRAM,
        notes=f"Instagram DM orqali keldi. Xabar: {message[:200]}",
    )
    LeadActivity.objects.create(
        lead=lead,
        created_by=None,
        type=ActivityType.NOTE,
        content=f"Instagram DM dan avtomatik yaratildi. Sender ID: {sender_id}",
    )
    logger.info("Yangi lead yaratildi: %s (%s)", lead.full_name, phone)
    return lead


class InstagramWebhookView(APIView):
    """
    Meta Instagram Webhook endpoint.
    GET  — webhook verification (challenge)
    POST — event qabul qilish (comments, messages)
    """
    permission_classes = (AllowAny,)

    def get(self, request):
        """Meta webhook verification."""
        mode      = request.GET.get("hub.mode")
        token     = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge")

        verify_token = getattr(settings, "INSTAGRAM_WEBHOOK_VERIFY_TOKEN", "")

        if mode == "subscribe" and token == verify_token:
            logger.info("Instagram webhook tasdiqlandi")
            return HttpResponse(challenge, content_type="text/plain")

        logger.warning("Instagram webhook tasdiqlanmadi. Token: %s", token)
        return Response({"error": "Forbidden"}, status=403)

    def post(self, request):
        """Instagram events qabul qilish."""
        from django.conf import settings as django_settings
        if not django_settings.DEBUG and not _verify_signature(request):
            logger.warning("Instagram webhook imzosi noto'g'ri")
            return Response({"error": "Invalid signature"}, status=403)

        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return Response({"error": "Invalid JSON"}, status=400)

        object_type = body.get("object")
        entries     = body.get("entry", [])

        access_token = getattr(settings, "INSTAGRAM_ACCESS_TOKEN", "")

        for entry in entries:
            changes  = entry.get("changes", [])
            messages = entry.get("messaging", [])

            # ── Comments ──
            for change in changes:
                if change.get("field") == "comments":
                    self._handle_comment(change["value"], access_token)

            # ── Direct Messages ──
            for msg_event in messages:
                self._handle_message(msg_event, access_token)

        return HttpResponse("EVENT_RECEIVED", content_type="text/plain")

    def _handle_comment(self, value: dict, access_token: str):
        """Post commentiga AI javob berish."""
        from apps.integrations.models import InstagramActivity

        comment_id   = value.get("id")
        comment_text = value.get("text", "")
        sender_id    = value.get("from", {}).get("id", "")
        sender_name  = value.get("from", {}).get("username", "")

        if not comment_id or not comment_text:
            return

        logger.info("Comment keldi: %s — '%s'", sender_id, comment_text[:50])

        ai_reply = _get_ai_reply(comment_text)
        replied  = _reply_comment(comment_id, ai_reply, access_token)

        dm_sent = False
        if sender_id:
            dm_text = (
                "Salom! 😊 Izohingiz uchun rahmat!\n"
                "Batafsil ma'lumot olish uchun telefon raqamingizni yuboring — "
                "mutaxassisimiz siz bilan bog'lanadi! 📚"
            )
            dm_sent = _send_dm(sender_id, dm_text, access_token)

        status = InstagramActivity.Status.REPLIED if replied else InstagramActivity.Status.FAILED
        if dm_sent:
            status = InstagramActivity.Status.DM_SENT

        InstagramActivity.objects.create(
            event_type   = InstagramActivity.EventType.COMMENT,
            sender_id    = sender_id,
            sender_name  = sender_name,
            message_text = comment_text,
            ai_reply     = ai_reply,
            status       = status,
        )

    def _handle_message(self, event: dict, access_token: str):
        """DM xabarini qayta ishlash — telefon raqam izlash."""
        from apps.integrations.models import InstagramActivity

        sender_id   = event.get("sender", {}).get("id", "")
        sender_name = event.get("sender", {}).get("name", "")
        message_obj = event.get("message", {})
        text        = message_obj.get("text", "")

        if not sender_id or not text:
            return

        logger.info("DM keldi: %s — '%s'", sender_id, text[:50])

        phone = _extract_phone(text)
        lead  = None

        if phone:
            lead = _create_lead_from_instagram(sender_id, sender_name, phone, text)
            confirm_text = (
                f"Rahmat! ✅ Raqamingiz qabul qilindi: {phone}\n"
                "Tez orada mutaxassisimiz siz bilan bog'lanadi! 🎓"
            )
            _send_dm(sender_id, confirm_text, access_token)
            status = InstagramActivity.Status.LEAD_CREATED
        else:
            reply = (
                "Salom! 😊 Biz siz bilan bog'lanish uchun telefon raqamingizni yuboring.\n"
                "Masalan: +998 90 123 45 67 📱"
            )
            _send_dm(sender_id, reply, access_token)
            status = InstagramActivity.Status.DM_SENT

        InstagramActivity.objects.create(
            event_type   = InstagramActivity.EventType.DM,
            sender_id    = sender_id,
            sender_name  = sender_name,
            message_text = text,
            status       = status,
            lead         = lead,
        )
