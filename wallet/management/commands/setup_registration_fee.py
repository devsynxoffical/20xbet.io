"""
Management command to set up registration fee in SystemSettings
Usage: python manage.py setup_registration_fee
"""
from django.core.management.base import BaseCommand
from wallet.models import SystemSettings


class Command(BaseCommand):
    help = 'Set up registration fee in SystemSettings'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fee',
            type=str,
            default='10.00',
            help='Registration fee amount (default: 10.00)',
        )

    def handle(self, *args, **options):
        fee_amount = options['fee']
        
        SystemSettings.objects.update_or_create(
            key='registration_fee',
            defaults={
                'value': fee_amount,
                'description': 'Registration fee amount in USDT (one-time payment required for account creation)'
            }
        )
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully set registration fee to {fee_amount} USDT')
        )

