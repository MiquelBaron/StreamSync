"""
Un solo flujo: migrate, grupos de rol, superuser admin,
usuario consumidor con ese rol, datos demo.
"""
from django.core.management import call_command
from django.core.management.base import BaseCommand

from ss.management.dev_database import (
    run_create_admin_user,
    run_create_consumer_user,
    run_create_platform_manager_user,
    run_create_roles,
    run_populate_demo_visualizations,
)


class Command(BaseCommand):
    help = (
        "Migrate, create role groups, admin + consumidor users, demo data."
    )

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("Applying migrations..."))
        call_command("migrate", interactive=False, verbosity=1)

        self.stdout.write(self.style.MIGRATE_HEADING("Creating roles..."))
        run_create_roles(self.stdout.write, self.style)

        self.stdout.write(self.style.MIGRATE_HEADING("Ensuring default admin user..."))
        run_create_admin_user(self.stdout.write, self.style)

        self.stdout.write(self.style.MIGRATE_HEADING("Ensuring consumidor (Consumidor de contingut)..."))
        run_create_consumer_user(self.stdout.write, self.style)

        self.stdout.write(self.style.MIGRATE_HEADING("Ensuring gestor (Gestor de plataformes)..."))
        run_create_platform_manager_user(self.stdout.write, self.style)

        self.stdout.write(self.style.MIGRATE_HEADING("Populating demo visualizations..."))
        run_populate_demo_visualizations(self.stdout.write, self.style)

        self.stdout.write(self.style.SUCCESS("Dev database preparation finished."))
