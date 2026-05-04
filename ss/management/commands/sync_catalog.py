from django.core.management.base import BaseCommand

from ss.catalog_sync import sync_catalog_from_apis


class Command(BaseCommand):
    help = "Sincronitza el catàleg local des de les APIs de les plataformes (per cron)."

    def handle(self, *args, **options):
        stats = sync_catalog_from_apis()
        self.stdout.write(
            self.style.SUCCESS(
                f"Plataformes: {stats['platforms']}, "
                f"pel·lícules upsert: {stats['movies_upserted']}, "
                f"sèries upsert: {stats['series_upserted']}, "
                f"pel·lícules desactivades (mirall): {stats.get('movies_soft_deactivated', 0)}, "
                f"sèries desactivades (mirall): {stats.get('series_soft_deactivated', 0)}"
            )
        )
        for err in stats.get("errors") or []:
            self.stdout.write(self.style.WARNING(err))
