from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class UserRole(models.TextChoices):
    ADMIN      = 'admin',      'Admin'
    RECEPTION  = 'reception',  'Reception'
    TEACHER    = 'teacher',    "O'qituvchi"
    STUDENT    = 'student',    'Talaba'


class UserManager(BaseUserManager):
    def create_user(self, phone, password=None, **extra_fields):
        if not phone:
            raise ValueError('Telefon raqam majburiy')
        user = self.model(phone=phone, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, password=None, **extra_fields):
        extra_fields.setdefault('role', UserRole.ADMIN)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(phone, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    phone      = models.CharField(max_length=13, unique=True, verbose_name='Telefon')
    first_name = models.CharField(max_length=50, verbose_name='Ism')
    last_name  = models.CharField(max_length=50, blank=True, verbose_name='Familiya')
    role       = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.RECEPTION, verbose_name='Rol')
    avatar     = models.ImageField(upload_to='avatars/', null=True, blank=True)
    is_active  = models.BooleanField(default=True)
    is_staff   = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD  = 'phone'
    REQUIRED_FIELDS = ['first_name']

    class Meta:
        verbose_name = 'Foydalanuvchi'
        verbose_name_plural = 'Foydalanuvchilar'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.first_name} {self.last_name} ({self.phone})'

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()
