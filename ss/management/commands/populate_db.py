"""
Després de sync_catalog: usuaris de prova (un per rol + un gestor per plataforma)
i visualitzacions demo aleatòries.
"""
from django.core.management.base import BaseCommand

from ss.management.dev_database import (
    run_populate_demo_visualizations,
    run_populate_dev_users,
)


class Command(BaseCommand):
    help = (
        "Crea usuaris de prova (consumidor, admin tècnic, director general, gestor_<id> per plataforma) "
        "i 100 visualitzacions aleatòries. Executar després de sync_catalog."
    )

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("Populating dev users (one per role + gestors)..."))
        run_populate_dev_users(self.stdout.write, self.style)

        self.stdout.write(self.style.MIGRATE_HEADING("Populating random demo visualizations (100)..."))
        run_populate_demo_visualizations(self.stdout.write, self.style)

        self.stdout.write(self.style.SUCCESS("populate_db finished."))
