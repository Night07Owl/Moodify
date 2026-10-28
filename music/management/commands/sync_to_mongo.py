"""
Django Management Command: sync_to_mongo
Synchronizes existing SQLite relational data (Support Tickets and Auth Users)
into MongoDB Atlas collections:
- 'users'
- 'support_tickets'
- 'login_history'
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from music.models import SupportTicket
from music import mongo_service


class Command(BaseCommand):
    help = 'Synchronizes existing SQLite Users and SupportTickets into MongoDB Atlas collections'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Connecting to MongoDB Atlas..."))

        db, is_mock = mongo_service.get_mongo_database(force_reconnect=True)
        if is_mock:
            self.stdout.write(self.style.WARNING("Warning: Operating with fallback mock engine. Check MongoDB URI."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Connected to live MongoDB cluster: database '{db.name}'"))

        # 1. Sync Users
        self.stdout.write(self.style.NOTICE("\nSyncing Users into MongoDB 'users' collection..."))
        users = list(User.objects.all())
        users_synced = 0
        for u in users:
            ok = mongo_service.sync_user_to_mongo(u)
            if ok:
                users_synced += 1
                self.stdout.write(f"  [Synced] User '{u.username}' (email: {u.email or 'none'})")

        # 2. Sync Support Tickets
        self.stdout.write(self.style.NOTICE("\nSyncing Support Tickets into MongoDB 'support_tickets' collection..."))
        tickets = list(SupportTicket.objects.all())
        tickets_synced = 0
        for t in tickets:
            res = mongo_service.record_support_ticket(t)
            if res:
                tickets_synced += 1
                self.stdout.write(f"  [Synced] Ticket #{t.ticket_number} - {t.subject} ({t.status})")

        # 3. Print Final Collection Counts
        stats = mongo_service.get_mongo_health_stats()
        self.stdout.write(self.style.SUCCESS("\n" + "="*50))
        self.stdout.write(self.style.SUCCESS("MongoDB Atlas Synchronization Complete!"))
        self.stdout.write(self.style.SUCCESS("="*50))
        self.stdout.write(f"  Storage Engine:     {stats['engine']}")
        self.stdout.write(f"  Database Name:      {stats['database']}")
        self.stdout.write(f"  Users in Mongo:     {stats['users_count']}")
        self.stdout.write(f"  Tickets in Mongo:   {stats['tickets_count']}")
        self.stdout.write(f"  Login Events:       {stats['login_history_count']}")
        self.stdout.write(f"  Chat Logs:          {stats['chat_logs_count']}")
        self.stdout.write(f"  Feedback Entries:   {stats['feedback_count']}")
        self.stdout.write(self.style.SUCCESS("="*50))

