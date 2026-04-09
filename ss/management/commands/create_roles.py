# ss/management/commands/create_roles.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group

class Command(BaseCommand):
    help = "Creates base roles for StreamSync"

    def handle(self, *args, **options):
        roles = [
            "Consumidor de contingut",
        ]

        for role_name in roles:
            _, created = Group.objects.get_or_create(name=role_name)
            if created:
                self.stdout.write(self.style.SUCCESS(f"Group '{role_name}' created correctly."))
            else:
                self.stdout.write(self.style.WARNING(f"Group '{role_name}' already exists."))