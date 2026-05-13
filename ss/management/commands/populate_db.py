"""
Després de sync_catalog: usuaris de prova, visualitzacions demo i ressenyes de pel·lícules (CA).
"""
from django.core.management.base import BaseCommand

from ss.management.dev_database import (
    run_populate_demo_film_reviews,
    run_populate_demo_visualizations,
    run_populate_dev_users,
)


class Command(BaseCommand):
    help = (
        "Crea usuaris de prova (consumidor, admin tècnic, director general, gestor_<id> per plataforma), "
        "100 visualitzacions aleatòries i ressenyes curtes de pel·lícules (CA). Executar després de sync_catalog."
    )

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("Populating dev users (one per role + gestors)..."))
        run_populate_dev_users(self.stdout.write, self.style)

        self.stdout.write(self.style.MIGRATE_HEADING("Populating random demo visualizations (100)..."))
        run_populate_demo_visualizations(self.stdout.write, self.style)

        self.stdout.write(self.style.MIGRATE_HEADING("Populating random film reviews (CA)..."))
        run_populate_demo_film_reviews(self.stdout.write, self.style)

        self.stdout.write(self.style.SUCCESS("populate_db finished."))
