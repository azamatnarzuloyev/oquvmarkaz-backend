from .base import *  # noqa

DEBUG = True

# withCredentials=true bilan wildcard '*' ishlamaydi — aniq origin kerak
CORS_ALLOWED_ORIGINS = [
    'http://localhost:5173',
    'http://127.0.0.1:5173',
]
CORS_ALLOW_CREDENTIALS = True

# Dev da SQLite ishlatish (PostgreSQL o'rnatilmagan bo'lsa)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
