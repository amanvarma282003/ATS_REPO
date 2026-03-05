"""
Management command: import_learning_resources

Reads pre-scraped learning resource data from
candidates/fixtures/learning_resources.json and upserts rows into
the LearningResource table.

The JSON file was generated once from the curated refer/ repos.
The refer/ folder is not required at runtime and can be deleted.

Usage:
  python manage.py import_learning_resources
  python manage.py import_learning_resources --clear   # wipe table first
"""

import json
import os

from django.conf import settings
from django.core.management.base import BaseCommand

from candidates.models import LearningResource

FIXTURE_PATH = os.path.join(
    settings.BASE_DIR, 'candidates', 'fixtures', 'learning_resources.json'
)


class Command(BaseCommand):
    help = 'Import learning resource links from the pre-scraped JSON fixture into the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Delete all existing LearningResource rows before importing',
        )

    def handle(self, *args, **options):
        if not os.path.isfile(FIXTURE_PATH):
            self.stderr.write(
                self.style.ERROR(f'Fixture not found: {FIXTURE_PATH}')
            )
            return

        if options['clear']:
            deleted, _ = LearningResource.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'Cleared {deleted} existing records.'))

        with open(FIXTURE_PATH, encoding='utf-8') as fh:
            records = json.load(fh)

        self.stdout.write(f'Loaded {len(records)} records from fixture.')

        created_count = 0
        updated_count = 0

        for rec in records:
            _, was_created = LearningResource.objects.update_or_create(
                url=rec['url'],
                source=rec['source'],
                defaults={
                    'title': rec['title'],
                    'category': rec['category'],
                },
            )
            if was_created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Done. Created: {created_count}, Updated: {updated_count}'
            )
        )
