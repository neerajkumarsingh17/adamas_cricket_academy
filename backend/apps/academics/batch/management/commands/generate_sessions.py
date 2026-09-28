from django.core.management.base import BaseCommand

from apps.academics.batch import services


class Command(BaseCommand):
    help = "Create TrainingSession rows from each active batch's weekly schedule."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days", type=int, default=28, help="How many days ahead to generate (default 28)."
        )

    def handle(self, *args, **options):
        result = services.generate_sessions(days=options["days"])
        self.stdout.write(
            self.style.SUCCESS(
                f"Created {result['created']} session(s), skipped {result['skipped']} "
                f"already-existing."
            )
        )
