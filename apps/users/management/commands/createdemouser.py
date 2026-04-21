from django.core.management.base import BaseCommand
from apps.users.models import User, UserRole

DEMO_USERS = [
    {
        'phone':      '+998901234567',
        'password':   'Demo1234!',
        'first_name': 'Admin',
        'last_name':  'User',
        'role':       UserRole.ADMIN,
        'is_staff':   True,
    },
    {
        'phone':      '+998901234568',
        'password':   'Demo1234!',
        'first_name': 'Reception',
        'last_name':  'User',
        'role':       UserRole.RECEPTION,
        'is_staff':   False,
    },
]


class Command(BaseCommand):
    help = "Demo foydalanuvchilarni yaratadi (admin va reception)"

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Mavjud demo foydalanuvchilarni o\'chirib qayta yaratadi',
        )

    def handle(self, *args, **options):
        for data in DEMO_USERS:
            phone = data['phone']

            user, created = User.objects.get_or_create(
                phone=phone,
                defaults={
                    'first_name': data['first_name'],
                    'last_name':  data['last_name'],
                    'role':       data['role'],
                    'is_staff':   data['is_staff'],
                },
            )
            # Har doim parolni yangilash (yangi yoki mavjud bo'lsa ham)
            user.set_password(data['password'])
            user.save(update_fields=['password'])

            label = '[CREATED]' if created else '[UPDATED]'
            self.stdout.write(
                self.style.SUCCESS(
                    f'{label} {user.phone} | Rol: {user.role} | Parol: {data["password"]}'
                )
            )

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('─' * 40))
        self.stdout.write(self.style.SUCCESS('Demo foydalanuvchilar:'))
        self.stdout.write(self.style.SUCCESS('─' * 40))
        for d in DEMO_USERS:
            self.stdout.write(f'  Telefon : {d["phone"]}')
            self.stdout.write(f'  Parol   : {d["password"]}')
            self.stdout.write(f'  Rol     : {d["role"]}')
            self.stdout.write('')
