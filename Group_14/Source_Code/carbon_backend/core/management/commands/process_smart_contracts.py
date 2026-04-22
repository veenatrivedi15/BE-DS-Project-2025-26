"""
Management command to process smart contracts and credit expiry
Run this command periodically (e.g., via cron job)
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from core.wallet_service import SmartContractService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Process smart contracts and credit expiry'

    def add_arguments(self, parser):
        parser.add_argument(
            '--process-expiry',
            action='store_true',
            help='Process credit expiry only',
        )
        parser.add_argument(
            '--process-transfers',
            action='store_true',
            help='Process auto-transfers only',
        )

    def handle(self, *args, **options):
        self.stdout.write('Starting smart contract processing...')
        
        try:
            # Process auto-transfers
            if not options.get('process_expiry'):
                self.stdout.write('Processing auto-transfers...')
                transfers = SmartContractService.process_auto_transfers()
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Processed {len(transfers)} auto-transfers'
                    )
                )
                
                for transfer in transfers:
                    self.stdout.write(
                        f'  - {transfer["amount"]} credits from {transfer["wallet_id"]} to {transfer["recipient"]}'
                    )
            
            # Process credit expiry
            if not options.get('process_transfers'):
                self.stdout.write('Processing credit expiry...')
                expired = SmartContractService.process_credit_expiry()
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Processed {len(expired)} expired credits'
                    )
                )
                
                for expiry in expired:
                    self.stdout.write(
                        f'  - {expiry["amount"]} credits expired from {expiry["wallet_id"]} on {expiry["expiry_date"]}'
                    )
            
            self.stdout.write(
                self.style.SUCCESS('Smart contract processing completed successfully')
            )
            
        except Exception as e:
            logger.error(f"Error in smart contract processing: {str(e)}")
            self.stdout.write(
                self.style.ERROR(f'Error: {str(e)}')
            )
