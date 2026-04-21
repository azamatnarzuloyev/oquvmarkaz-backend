import requests
from django.conf import settings


SMS_TEMPLATES = {
    'WELCOME':            "Salom {name}! Arizangiz qabul qilindi. Tez orada bog'lanamiz.",
    'PAYMENT_RECEIVED':   "{name}, {amount:,} so'm to'lov qabul qilindi.",
    'PAYMENT_REMINDER':   "{name}, {month} uchun {amount:,} so'm to'lov muddati o'tdi.",
    'TRIAL_REMINDER':     "{name}, ertaga soat {time} da sinov darsiga taklif qilamiz.",
    'ATTENDANCE_WARNING': "{name}, so'nggi 3 kunda darsga kelmadingiz. Aloqa qiling.",
}


class EskizClient:
    BASE_URL = 'https://notify.eskiz.uz/api'
    _token: str | None = None

    def _authenticate(self) -> str:
        resp = requests.post(
            f'{self.BASE_URL}/auth/login',
            data={'email': settings.ESKIZ_EMAIL, 'password': settings.ESKIZ_PASSWORD},
            timeout=10,
        )
        resp.raise_for_status()
        self._token = resp.json()['data']['token']
        return self._token

    def _get_token(self) -> str:
        if not self._token:
            return self._authenticate()
        return self._token

    def send(self, phone: str, message: str) -> dict:
        phone_clean = phone.replace('+', '').replace(' ', '')
        headers = {'Authorization': f'Bearer {self._get_token()}'}
        try:
            resp = requests.post(
                f'{self.BASE_URL}/message/sms/send',
                headers=headers,
                json={'mobile_phone': phone_clean, 'message': message, 'from': '4546'},
                timeout=10,
            )
            if resp.status_code == 401:
                self._authenticate()
                headers['Authorization'] = f'Bearer {self._token}'
                resp = requests.post(
                    f'{self.BASE_URL}/message/sms/send',
                    headers=headers,
                    json={'mobile_phone': phone_clean, 'message': message, 'from': '4546'},
                    timeout=10,
                )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            raise RuntimeError(f'SMS yuborishda xatolik: {e}') from e


def render_sms(template_key: str, **kwargs) -> str:
    template = SMS_TEMPLATES.get(template_key)
    if not template:
        raise ValueError(f'Noma\'lum SMS template: {template_key}')
    return template.format(**kwargs)
