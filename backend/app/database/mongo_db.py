"""
MongoDB database layer — drop-in replacement for csv_db.py.
Exposes the same Collection API so all route files only need to change
their import line.
"""
import os
import uuid
from datetime import datetime

from pymongo import MongoClient, ReturnDocument


class Collection:
    def __init__(self, col, has_updated_at=False):
        self._col = col
        self._has_updated_at = has_updated_at

    # ── Internal ──────────────────────────────────────────────────────────────

    def _to_doc(self, doc):
        if doc is None:
            return None
        d = dict(doc)
        d['id'] = str(d.pop('_id', ''))
        return d

    # ── Public API ────────────────────────────────────────────────────────────

    def read_all(self) -> list:
        return [self._to_doc(d) for d in self._col.find()]

    def insert(self, data: dict) -> dict:
        data = data.copy()
        data.pop('id', None)
        data['_id'] = str(uuid.uuid4())
        data.setdefault('created_at', datetime.utcnow().isoformat() + 'Z')
        if self._has_updated_at:
            data.setdefault('updated_at', '')
        self._col.insert_one(data)
        return self._to_doc(data)

    def find_by_id(self, record_id: str):
        return self._to_doc(self._col.find_one({'_id': record_id}))

    def find_one(self, **kwargs):
        return self._to_doc(self._col.find_one(kwargs))

    def find(self, **kwargs) -> list:
        return [self._to_doc(d) for d in self._col.find(kwargs)]

    def find_by_filter(self, fn) -> list:
        return [doc for doc in (self._to_doc(d) for d in self._col.find()) if fn(doc)]

    def update_by_id(self, record_id: str, updates: dict):
        updates = dict(updates)
        if self._has_updated_at:
            updates['updated_at'] = datetime.utcnow().isoformat() + 'Z'
        doc = self._col.find_one_and_update(
            {'_id': record_id},
            {'$set': updates},
            return_document=ReturnDocument.AFTER,
        )
        return self._to_doc(doc)

    def delete_by_id(self, record_id: str) -> bool:
        return self._col.delete_one({'_id': record_id}).deleted_count > 0

    def delete_where(self, **kwargs) -> int:
        return self._col.delete_many(kwargs).deleted_count

    def count(self, **kwargs) -> int:
        return self._col.count_documents(kwargs if kwargs else {})


class Database:
    """Central access point for all MongoDB collections."""

    def __init__(self, mongo_db):
        def c(name, has_updated_at=False):
            return Collection(mongo_db[name], has_updated_at=has_updated_at)

        self.users              = c('users',          has_updated_at=True)
        self.user_follows       = c('user_follows')
        self.follow_requests    = c('follow_requests', has_updated_at=True)
        self.blogs              = c('blogs',           has_updated_at=True)
        self.blog_likes         = c('blog_likes')
        self.comments           = c('comments')
        self.messages           = c('messages')
        self.groups             = c('groups',          has_updated_at=True)
        self.group_members      = c('group_members')
        self.notifications      = c('notifications')
        self.push_subscriptions = c('push_subscriptions')
        self.site_config        = c('site_config')
        self.wishes             = c('wishes',  has_updated_at=True)
        self.wish_shares        = c('wish_shares')


# ── Singleton ─────────────────────────────────────────────────────────────────
_db: Database | None = None


def get_db() -> Database:
    global _db
    if _db is None:
        client = MongoClient(os.getenv('MONGO_URI', 'mongodb://localhost:27017'))
        mongo = client[os.getenv('MONGO_DB_NAME', 'blog_media')]
        _db = Database(mongo)
    return _db


db: Database = get_db()
