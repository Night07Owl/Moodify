"""
MongoDB Service for MoodMusic.
Handles NoSQL persistence of:
1. Support tickets (mirrored from SQL)
2. Registered users and authentication credentials
3. User login activity and sessions
4. Unstructured chat conversations and session history
5. User feedback metrics and ratings

Uses pymongo with MongoDB Atlas, with automatic graceful fallback
to mongomock if standalone/cloud MongoDB is temporarily unreachable.
"""

import os
from datetime import datetime
from django.conf import settings

_mongo_client = None
_mongo_db = None
_is_mock = False


def get_mongo_database(force_reconnect=False):
    """
    Returns the MongoDB database instance (real MongoDB or in-memory fallback).
    Ensures safe singleton connection. If a mock was previously active due to a transient
    network delay, subsequent calls will attempt to re-establish a live Atlas connection.
    """
    global _mongo_client, _mongo_db, _is_mock

    # If we already have an active LIVE connection and no forced reconnect, reuse it
    if _mongo_db is not None and not _is_mock and not force_reconnect:
        return _mongo_db, _is_mock

    mongo_uri = getattr(settings, 'MONGODB_URI', os.environ.get('MONGODB_URI', 'mongodb://127.0.0.1:27017/moodmusic_db')).strip()
    db_name = getattr(settings, 'MONGODB_NAME', os.environ.get('MONGODB_NAME', 'moodmusic_db')).strip()

    # Attempt real pymongo connection with 7500ms timeout and certifi TLS CA
    try:
        import pymongo
        client_kwargs = {
            'serverSelectionTimeoutMS': 7500,
            'connectTimeoutMS': 7500,
            'socketTimeoutMS': 10000,
        }
        try:
            import certifi
            client_kwargs['tlsCAFile'] = certifi.where()
        except Exception:
            pass

        client = pymongo.MongoClient(mongo_uri, **client_kwargs)
        # Verify connection by triggering a quick ping to the admin database
        client.admin.command('ping')
        _mongo_client = client
        _mongo_db = client[db_name]
        _is_mock = False
        print(f"[MongoService] Successfully connected to live MongoDB database '{db_name}'.")
        return _mongo_db, _is_mock
    except Exception as e:
        print(f"[MongoService] WARNING: Live MongoDB connection failed ({e}). Falling back to in-memory mock.")
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
                def find_one(self, query=None, *args, **kwargs):
                    if not query:
                        return self.docs[0] if self.docs else None
                    for d in self.docs:
                        matched = True
                        for k, v in query.items():
                            if k == '$or':
                                if not any(d.get(ok) == ov for or_elem in v for ok, ov in or_elem.items()):
                                    matched = False
                            elif d.get(k) != v:
                                matched = False
                        if matched:
                            return d
                    return None
                def update_one(self, query, update, upsert=False):
                    doc = self.find_one(query)
                    if not doc and upsert:
                        doc = dict(query)
                        if '$setOnInsert' in update:
                            doc.update(update['$setOnInsert'])
                        self.docs.append(doc)
                    if doc and '$set' in update:
                        doc.update(update['$set'])
                    class Res:
                        upserted_id = 'mem-id'
                    return Res()
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
        t_num = getattr(ticket, 'ticket_number', '') or (ticket.get('ticket_number') if isinstance(ticket, dict) else '')
        u_name = getattr(ticket, 'user_name', '') or (ticket.get('user_name', 'Anonymous User') if isinstance(ticket, dict) else 'Anonymous User')
        u_email = getattr(ticket, 'user_email', '') or (ticket.get('user_email', '') if isinstance(ticket, dict) else '')
        subj = getattr(ticket, 'subject', '') or (ticket.get('subject', '') if isinstance(ticket, dict) else '')
        cat = getattr(ticket, 'category', '') or (ticket.get('category', 'Support Inquiry') if isinstance(ticket, dict) else 'Support Inquiry')
        prio = getattr(ticket, 'priority', '') or (ticket.get('priority', 'Medium') if isinstance(ticket, dict) else 'Medium')
        desc = getattr(ticket, 'description', '') or (ticket.get('description', '') if isinstance(ticket, dict) else '')
        stat = getattr(ticket, 'status', '') or (ticket.get('status', 'Open') if isinstance(ticket, dict) else 'Open')
        ai_gen = getattr(ticket, 'ai_generated', False) if hasattr(ticket, 'ai_generated') else (ticket.get('ai_generated', False) if isinstance(ticket, dict) else False)
        sql_id = getattr(ticket, 'id', None)

        if not t_num:
            import uuid
            t_num = f"TCK-{uuid.uuid4().hex[:8].upper()}"

        doc = {
            'ticket_number': t_num,
            'user_name': u_name,
            'user_email': u_email,
            'subject': subj,
            'category': cat,
            'priority': prio,
            'description': desc,
            'status': stat,
            'ai_generated': bool(ai_gen),
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
    Stores username, email, display_name, and secure hashed password.
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
            'last_login': datetime.utcnow(),
            'login_count': 1,
            'role': 'user',
            'storage_engine': 'mongomock' if is_mock else 'mongodb',
        }
        res = users_coll.insert_one(user_doc)
        user_id_str = str(getattr(res, 'inserted_id', ''))

        # Also record the signup event in login_history
        record_login_activity(
            username=u_clean,
            email=e_clean,
            success=True,
            details="User registration / initial account creation"
        )

        return True, user_id_str
    except Exception as err:
        print(f"[MongoService] Error creating user: {err}")
        return False, str(err)


def sync_user_to_mongo(django_user, raw_password=None):
    """
    Syncs a Django auth User model instance into MongoDB 'users' collection.
    Called when a user is saved (e.g. admin, createsuperuser, or login sync).
    """
    try:
        db, is_mock = get_mongo_database()
        users_coll = db['users']

        u_clean = django_user.username.strip().lower()
        e_clean = (django_user.email or '').strip().lower()

        update_fields = {
            'username': u_clean,
            'display_name': django_user.get_full_name() or django_user.username,
            'email': e_clean,
            'is_staff': django_user.is_staff,
            'is_superuser': django_user.is_superuser,
            'is_active': django_user.is_active,
            'updated_at': datetime.utcnow(),
            'storage_engine': 'mongomock' if is_mock else 'mongodb',
        }

        if raw_password:
            from django.contrib.auth.hashers import make_password
            update_fields['password'] = make_password(raw_password)
        elif django_user.password:
            update_fields['password'] = django_user.password

        if django_user.last_login:
            update_fields['last_login'] = django_user.last_login

        users_coll.update_one(
            {'username': u_clean},
            {
                '$set': update_fields,
                '$setOnInsert': {
                    'created_at': django_user.date_joined if hasattr(django_user, 'date_joined') and django_user.date_joined else datetime.utcnow(),
                    'login_count': 0,
                    'role': 'admin' if django_user.is_staff else 'user',
                }
            },
            upsert=True
        )
        return True
    except Exception as err:
        print(f"[MongoService] Error syncing user to Mongo: {err}")
        return False


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


def record_login_activity(username, email='', success=True, ip_address='127.0.0.1', user_agent='Unknown', details=''):
    """
    Persists a login attempt (successful or failed) in MongoDB 'login_history' collection.
    Also updates the user's last_login timestamp and login_count in 'users' collection on success.
    """
    try:
        db, is_mock = get_mongo_database()
        logins_coll = db['login_history']

        u_clean = (username or '').strip().lower()
        e_clean = (email or '').strip().lower()

        doc = {
            'username': u_clean,
            'email': e_clean,
            'success': bool(success),
            'ip_address': ip_address,
            'user_agent': user_agent,
            'details': details,
            'timestamp': datetime.utcnow(),
            'storage_engine': 'mongomock' if is_mock else 'mongodb',
        }
        res = logins_coll.insert_one(doc)

        # On successful login, also update last_login and increment login_count in users collection
        if success and (u_clean or e_clean):
            users_coll = db['users']
            users_coll.update_one(
                {'$or': [{'username': u_clean}, {'email': e_clean}]},
                {
                    '$set': {
                        'last_login': datetime.utcnow(),
                        'last_login_ip': ip_address,
                    },
                    '$inc': {'login_count': 1}
                }
            )

        return str(getattr(res, 'inserted_id', ''))
    except Exception as err:
        print(f"[MongoService] Error recording login activity: {err}")
        return None


def get_mongo_health_stats():
    """
    Returns diagnostic statistics for the /health/ view and admin telemetry.
    """
    try:
        db, is_mock = get_mongo_database()
        chat_count = db['chat_logs'].count_documents({}) if hasattr(db['chat_logs'], 'count_documents') else len(list(db['chat_logs'].find()))
        feedback_count = db['chat_feedback'].count_documents({}) if hasattr(db['chat_feedback'], 'count_documents') else len(list(db['chat_feedback'].find()))
        tickets_count = db['support_tickets'].count_documents({}) if hasattr(db['support_tickets'], 'count_documents') else len(list(db['support_tickets'].find()))
        users_count = db['users'].count_documents({}) if hasattr(db['users'], 'count_documents') else len(list(db['users'].find()))
        logins_count = db['login_history'].count_documents({}) if hasattr(db['login_history'], 'count_documents') else len(list(db['login_history'].find()))

        return {
            'status': 'healthy',
            'engine': 'mongomock (In-Memory Fallback)' if is_mock else 'MongoDB Server (Live)',
            'database': getattr(settings, 'MONGODB_NAME', 'moodmusic_db'),
            'chat_logs_count': chat_count,
            'feedback_count': feedback_count,
            'tickets_count': tickets_count,
            'users_count': users_count,
            'login_history_count': logins_count,
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
            'login_history_count': 0,
            'is_mock': True
        }
