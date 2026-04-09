# ss/management/commands/create_admin_user.py
from django.core.management.base import BaseCommand

from ss.management.dev_database import run_create_admin_user


class Command(BaseCommand):
    help = "Creates a default admin user (username: admin, password: admin)"

    def handle(self, *args, **options):
        run_create_admin_user(self.stdout.write, self.style)
