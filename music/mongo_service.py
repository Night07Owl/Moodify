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

    # First attempt real pymongo connection with 1.5s timeout
    try:
        import pymongo
        client = pymongo.MongoClient(mongo_uri, serverSelectionTimeoutMS=1500)
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


def get_mongo_health_stats():
    """
    Returns diagnostic statistics for the /health/ view.
    """
    try:
        db, is_mock = get_mongo_database()
        chat_count = db['chat_logs'].count_documents({}) if hasattr(db['chat_logs'], 'count_documents') else len(list(db['chat_logs'].find()))
        feedback_count = db['chat_feedback'].count_documents({}) if hasattr(db['chat_feedback'], 'count_documents') else len(list(db['chat_feedback'].find()))

        return {
            'status': 'healthy',
            'engine': 'mongomock (In-Memory Fallback)' if is_mock else 'MongoDB Server (Live)',
            'database': getattr(settings, 'MONGODB_NAME', 'moodmusic_db'),
            'chat_logs_count': chat_count,
            'feedback_count': feedback_count,
            'is_mock': is_mock,
        }
    except Exception as err:
        return {
            'status': 'degraded',
            'error': str(err),
            'engine': 'offline',
            'chat_logs_count': 0,
            'feedback_count': 0,
            'is_mock': True
        }
