from django.core.management.base import BaseCommand
from mlm.models import MLMLevel

class Command(BaseCommand):
    help = 'Initialize MLM Levels'

    def handle(self, *args, **kwargs):
        levels = [
            {'level': 1, 'name': 'Starter', 'price': 100, 'commission_percent': 10},
            {'level': 2, 'name': 'Bronze', 'price': 200, 'commission_percent': 8},
            {'level': 3, 'name': 'Silver', 'price': 500, 'commission_percent': 5},
            {'level': 4, 'name': 'Gold', 'price': 1000, 'commission_percent': 3},
            {'level': 5, 'name': 'Diamond', 'price': 2000, 'commission_percent': 2},
        ]

        for data in levels:
            MLMLevel.objects.update_or_create(level=data['level'], defaults=data)
            self.stdout.write(self.style.SUCCESS(f"Level {data['level']} initialized"))
