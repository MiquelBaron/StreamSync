"""
Migracions, grups de rol i superusuari mínim (admin).
Després: sync_catalog → populate_db (usuaris per rol + visualitzacions).
"""
from django.core.management import call_command
from django.core.management.base import BaseCommand

from ss.management.dev_database import (
    run_create_admin_user,
    run_create_roles,
)


class Command(BaseCommand):
    help = "Aplica migracions i crea els grups de rol + superusuari admin (sense catàleg ni usuaris de prova)."

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("Applying migrations..."))
        call_command("migrate", interactive=False, verbosity=1)

        self.stdout.write(self.style.MIGRATE_HEADING("Creating roles..."))
        run_create_roles(self.stdout.write, self.style)

        self.stdout.write(self.style.MIGRATE_HEADING("Ensuring default admin user..."))
        run_create_admin_user(self.stdout.write, self.style)

        self.stdout.write(
            self.style.SUCCESS(
                "Preparació base acabada. Següent: python manage.py sync_catalog "
                "i després python manage.py populate_db"
            )
        )
