from django.core.management.base import BaseCommand

from web.reactivation_services import mark_inactive_centres


class Command(BaseCommand):
    help = "Disable active centre accounts that have exceeded the inactivity period."

    def handle(self, *args, **options):
        marked = mark_inactive_centres()
        self.stdout.write(
            self.style.SUCCESS(f"Marked {marked} centre(s) inactive due to inactivity.")
        )
