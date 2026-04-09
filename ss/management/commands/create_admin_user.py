# ss/management/commands/create_admin_user.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = "Creates a default admin user (username: admin, password: admin)"

    def handle(self, *args, **options):
        User = get_user_model()
        username = "admin"
        password = "admin"

        if not User.objects.filter(username=username).exists():
            User.objects.create_superuser(username=username, password=password)
            self.stdout.write(self.style.SUCCESS(f"Superuser '{username}' created successfully."))
        else:
            self.stdout.write(self.style.WARNING(f"Superuser '{username}' already exists."))