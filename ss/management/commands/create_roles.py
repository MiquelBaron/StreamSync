# ss/management/commands/create_roles.py
from django.core.management.base import BaseCommand

from ss.management.dev_database import run_create_roles


class Command(BaseCommand):
    help = "Creates base roles for StreamSync"

    def handle(self, *args, **options):
        run_create_roles(self.stdout.write, self.style)
