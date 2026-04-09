from django.core.management.base import BaseCommand

from ss.management.dev_database import run_populate_demo_data


class Command(BaseCommand):
    help = "Populate database with demo data for StreamSync"

    def handle(self, *args, **options):
        run_populate_demo_data(self.stdout.write, self.style)
