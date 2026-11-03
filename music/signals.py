"""
Django Signals for MoodMusic.
Ensures seamless, automatic synchronization between relational SQLite data
and MongoDB NoSQL collections for:
1. Support Tickets (mirrored to MongoDB 'support_tickets')
2. Users (mirrored to MongoDB 'users')
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import SupportTicket
from . import mongo_service


@receiver(post_save, sender=SupportTicket)
def auto_sync_support_ticket_to_mongo(sender, instance, created, **kwargs):
    """
    Automatically mirrors every SupportTicket saved in SQL to MongoDB.
    Fires whether created through web UI, API, AI assistant, or Django admin.
    """
    try:
        mongo_service.record_support_ticket(instance)
    except Exception as err:
        print(f"[Signals] Error auto-syncing SupportTicket #{instance.ticket_number} to Mongo: {err}")


@receiver(post_delete, sender=SupportTicket)
def auto_delete_support_ticket_from_mongo(sender, instance, **kwargs):
    """
    Automatically removes a deleted SupportTicket from MongoDB.
    """
    try:
        mongo_service.delete_support_ticket(instance.ticket_number)
    except Exception as err:
        print(f"[Signals] Error deleting SupportTicket #{instance.ticket_number} from Mongo: {err}")


@receiver(post_save, sender=User)
def auto_sync_user_to_mongo(sender, instance, created, **kwargs):
    """
    Automatically syncs any Django auth User (admin, createsuperuser, demouser) to MongoDB 'users'.
    """
    try:
        mongo_service.sync_user_to_mongo(instance)
    except Exception as err:
        print(f"[Signals] Error auto-syncing User '{instance.username}' to Mongo: {err}")

