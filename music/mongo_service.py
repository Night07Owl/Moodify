"""
MongoDB Service for MoodMusic.
Handles NoSQL persistence of unstructured chat conversations, session history,
and user feedback metrics.

Uses pymongo with automatic graceful fallback to mongomock if a standalone
MongoDB server instance is not currently active.
"""

import os
from datetime import datetime
from django.conf import settings

_mongo_client = None
_mongo_db = None
_is_mock = False

def get_mongo_database():
    """
    Returns the MongoDB database instance (real or mongomock).
    Ensures safe singleton connection.
    """
    global _mongo_client, _mongo_db, _is_mock

    if _mongo_db is not None:
        return _mongo_db, _is_mock

    mongo_uri = getattr(settings, 'MONGODB_URI', os.environ.get('MONGODB_URI', 'mongodb://127.0.0.1:27017/moodmusic_db'))
    db_name = getattr(settings, 'MONGODB_NAME', os.environ.get('MONGODB_NAME', 'moodmusic_db'))

    # First attempt real pymongo connection with 2.5s timeout and certifi TLS CA
    try:
        import pymongo
        client_kwargs = {'serverSelectionTimeoutMS': 2500}
        try:
            import certifi
            client_kwargs['tlsCAFile'] = certifi.where()
        except Exception:
            pass
        client = pymongo.MongoClient(mongo_uri.strip(), **client_kwargs)
        # Verify connection by triggering a quick ping
        client.admin.command('ping')
        _mongo_client = client
        _mongo_db = client[db_name]
        _is_mock = False
        return _mongo_db, _is_mock
    except Exception as e:
        # Graceful fallback to mongomock for seamless zero-setup evaluation
        try:
            import mongomock
            mock_client = mongomock.MongoClient()
            _mongo_client = mock_client
            _mongo_db = mock_client[db_name]
            _is_mock = True
            return _mongo_db, _is_mock
        except Exception:
            # Fallback in-memory dict if even mongomock has an issue
            class SimpleInMemoryCollection:
                def __init__(self):
                    self.docs = []
                def insert_one(self, doc):
                    self.docs.append(doc)
                    class Res:
                        inserted_id = len(self.docs)
                    return Res()
                def find(self, *args, **kwargs):
                    return iter(self.docs[-50:])
                def count_documents(self, *args, **kwargs):
                    return len(self.docs)

            class SimpleInMemoryDB:
                def __init__(self):
                    self.collections = {}
                def __getitem__(self, name):
                    if name not in self.collections:
                        self.collections[name] = SimpleInMemoryCollection()
                    return self.collections[name]

            _mongo_db = SimpleInMemoryDB()
            _is_mock = True
            return _mongo_db, _is_mock


def log_chat_interaction(session_id, user_message, bot_reply, error_code=None, resolved=True, created_ticket=False, metadata=None):
    """
    Persists a chat turn into the MongoDB 'chat_logs' collection.
    """
    try:
        db, is_mock = get_mongo_database()
        collection = db['chat_logs']
        
        doc = {
            'session_id': session_id,
            'user_message': user_message,
            'bot_reply': bot_reply,
            'error_code': error_code,
            'resolved': resolved,
            'created_ticket': created_ticket,
            'metadata': metadata or {},
            'timestamp': datetime.utcnow(),
            'storage_engine': 'mongomock' if is_mock else 'mongodb',
        }
        res = collection.insert_one(doc)
        return str(getattr(res, 'inserted_id', ''))
    except Exception as err:
        print(f"[MongoService] Error logging chat interaction: {err}")
        return None


def record_chat_feedback(session_id, message_id=None, rating=5, feedback_type='helpful', comments='', user_email=''):
    """
    Persists user rating and sentiment into the MongoDB 'chat_feedback' collection.
    """
    try:
        db, is_mock = get_mongo_database()
        collection = db['chat_feedback']

        doc = {
            'session_id': session_id,
            'message_id': message_id,
            'rating': int(rating),  # 1 to 5
            'feedback_type': feedback_type,  # 'thumbs_up', 'thumbs_down', 'helpful', 'bug'
            'comments': comments,
            'user_email': user_email,
            'timestamp': datetime.utcnow(),
            'storage_engine': 'mongomock' if is_mock else 'mongodb',
        }
        res = collection.insert_one(doc)
        return str(getattr(res, 'inserted_id', ''))
    except Exception as err:
        print(f"[MongoService] Error logging feedback: {err}")
        return None


def get_recent_chat_logs(limit=25):
    """
    Fetches the latest chat interaction logs from MongoDB.
    """
    try:
        db, is_mock = get_mongo_database()
        collection = db['chat_logs']
        docs = list(collection.find().limit(limit))
        # Format for display
        for d in docs:
            if '_id' in d:
                d['id'] = str(d['_id'])
            if 'timestamp' in d and hasattr(d['timestamp'], 'strftime'):
                d['timestamp_str'] = d['timestamp'].strftime('%Y-%m-%d %H:%M:%S UTC')
        return docs
    except Exception as err:
        print(f"[MongoService] Error getting chat logs: {err}")
        return []


def record_support_ticket(ticket):
    """
    Persists or updates a Support Ticket into the MongoDB 'support_tickets' collection.
    Ensures support tickets are mirrored into MongoDB while primary state is preserved in SQL.
    """
    try:
        db, is_mock = get_mongo_database()
        collection = db['support_tickets']

        # Extract attributes from model or dict
        t_num = getattr(ticket, 'ticket_number', '') or ticket.get('ticket_number')
        u_name = getattr(ticket, 'user_name', '') or ticket.get('user_name', 'Anonymous User')
        u_email = getattr(ticket, 'user_email', '') or ticket.get('user_email', '')
        subj = getattr(ticket, 'subject', '') or ticket.get('subject', '')
        cat = getattr(ticket, 'category', '') or ticket.get('category', 'Support Inquiry')
        prio = getattr(ticket, 'priority', '') or ticket.get('priority', 'Medium')
        desc = getattr(ticket, 'description', '') or ticket.get('description', '')
        stat = getattr(ticket, 'status', '') or ticket.get('status', 'Open')
        ai_gen = getattr(ticket, 'ai_generated', False) if hasattr(ticket, 'ai_generated') else ticket.get('ai_generated', False)
        sql_id = getattr(ticket, 'id', None)

        doc = {
            'ticket_number': t_num,
            'user_name': u_name,
            'user_email': u_email,
            'subject': subj,
            'category': cat,
            'priority': prio,
            'description': desc,
            'status': stat,
            'ai_generated': ai_gen,
            'sql_id': sql_id,
            'updated_at': datetime.utcnow(),
            'storage_engine': 'mongomock' if is_mock else 'mongodb',
        }

        res = collection.update_one(
            {'ticket_number': t_num},
            {'$set': doc, '$setOnInsert': {'created_at': datetime.utcnow()}},
            upsert=True
        )
        return str(getattr(res, 'upserted_id', t_num))
    except Exception as err:
        print(f"[MongoService] Error logging support ticket: {err}")
        return None


def create_mongo_user(username, email, password):
    """
    Registers a new user in MongoDB 'users' collection.
    Stores username, email, and secure hashed password.
    """
    try:
        from django.contrib.auth.hashers import make_password
        db, is_mock = get_mongo_database()
        users_coll = db['users']

        u_clean = username.strip().lower()
        e_clean = email.strip().lower()

        # Check for existing user with same username or email
        existing = users_coll.find_one({
            '$or': [
                {'username': u_clean},
                {'email': e_clean}
            ]
        })
        if existing:
            if existing.get('username') == u_clean:
                return False, "Username is already taken. Please choose another."
            return False, "An account with this email already exists."

        user_doc = {
            'username': u_clean,
            'display_name': username.strip(),
            'email': e_clean,
            'password': make_password(password),
            'created_at': datetime.utcnow(),
            'storage_engine': 'mongomock' if is_mock else 'mongodb',
        }
        res = users_coll.insert_one(user_doc)
        return True, str(getattr(res, 'inserted_id', ''))
    except Exception as err:
        print(f"[MongoService] Error creating user: {err}")
        return False, str(err)


def authenticate_mongo_user(username_or_email, password):
    """
    Authenticates user against MongoDB 'users' collection.
    Returns user document if credentials match, None otherwise.
    """
    try:
        from django.contrib.auth.hashers import check_password
        db, is_mock = get_mongo_database()
        users_coll = db['users']

        query = username_or_email.strip().lower()
        user_doc = users_coll.find_one({
            '$or': [
                {'username': query},
                {'email': query}
            ]
        })
        if not user_doc:
            return None

        if check_password(password, user_doc.get('password', '')):
            return user_doc
        return None
    except Exception as err:
        print(f"[MongoService] Error authenticating user: {err}")
        return None


def get_mongo_health_stats():
    """
    Returns diagnostic statistics for the /health/ view.
    """
    try:
        db, is_mock = get_mongo_database()
        chat_count = db['chat_logs'].count_documents({}) if hasattr(db['chat_logs'], 'count_documents') else len(list(db['chat_logs'].find()))
        feedback_count = db['chat_feedback'].count_documents({}) if hasattr(db['chat_feedback'], 'count_documents') else len(list(db['chat_feedback'].find()))
        tickets_count = db['support_tickets'].count_documents({}) if hasattr(db['support_tickets'], 'count_documents') else len(list(db['support_tickets'].find()))
        users_count = db['users'].count_documents({}) if hasattr(db['users'], 'count_documents') else len(list(db['users'].find()))

        return {
            'status': 'healthy',
            'engine': 'mongomock (In-Memory Fallback)' if is_mock else 'MongoDB Server (Live)',
            'database': getattr(settings, 'MONGODB_NAME', 'moodmusic_db'),
            'chat_logs_count': chat_count,
            'feedback_count': feedback_count,
            'tickets_count': tickets_count,
            'users_count': users_count,
            'is_mock': is_mock,
        }
    except Exception as err:
        return {
            'status': 'degraded',
            'error': str(err),
            'engine': 'offline',
            'chat_logs_count': 0,
            'feedback_count': 0,
            'tickets_count': 0,
            'users_count': 0,
            'is_mock': True
        }
