"""
Caching system for AI responses and computed data.

Uses database-backed storage with TTL support.
Also provides an in-memory LRU cache for fast, per-process caching.
"""

import json
import hashlib
import time
from datetime import datetime, timedelta
from functools import lru_cache
from flask import current_app, g
from extensions import db
from sqlalchemy.exc import SQLAlchemyError


class CacheEntry(db.Model):
    """Model for storing cached values in database"""
    __tablename__ = 'cache_entries'

    id = db.Column(db.Integer, primary_key=True)
    cache_key = db.Column(db.String(255), unique=True, nullable=False, index=True)
    cache_value = db.Column(db.Text, nullable=False)  # JSON serialized
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def is_expired(self):
        """Check if this cache entry has expired"""
        return datetime.utcnow() > self.expires_at

    def to_dict(self):
        """Deserialize cached value"""
        return json.loads(self.cache_value)

    @classmethod
    def serialize(cls, value):
        """Serialize value to JSON string"""
        return json.dumps(value, ensure_ascii=False)

    @classmethod
    def deserialize(cls, json_str):
        """Deserialize JSON string to value"""
        return json.loads(json_str)


# In-memory cache for fast context caching (per-process, not shared)
# Used for conversation context that changes rapidly
class MemoryCache:
    """Simple in-memory LRU cache with TTL support"""

    def __init__(self, maxsize=128):
        self._cache = {}
        self._maxsize = maxsize

    def get(self, key):
        """Get value from memory cache if exists and not expired"""
        if key not in self._cache:
            return None

        entry = self._cache[key]
        if time.time() > entry['expires_at']:
            # Expired, remove and return None
            del self._cache[key]
            return None

        return entry['value']

    def set(self, key, value, ttl_seconds):
        """Set value in memory cache with TTL"""
        # Evict oldest if cache is full (simple LRU)
        if len(self._cache) >= self._maxsize:
            # Remove first item (oldest in Python 3.7+ dicts)
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]

        self._cache[key] = {
            'value': value,
            'expires_at': time.time() + ttl_seconds,
            'created_at': time.time()
        }

    def delete(self, key):
        """Remove key from cache"""
        if key in self._cache:
            del self._cache[key]

    def clear(self):
        """Clear all entries"""
        self._cache.clear()


class Cache:
    """Main cache interface that uses database backend with memory fallback"""

    def __init__(self, app=None, db_session=None):
        """
        Initialize cache.

        Args:
            app: Flask app instance (optional, can bind later)
            db_session: SQLAlchemy session factory (optional)
        """
        self.db = db_session
        self._memory_cache = MemoryCache(maxsize=256)
        self._enabled = True
        self._stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'db_errors': 0
        }

        if app:
            self.init_app(app)

    def init_app(self, app):
        """Initialize with Flask app config"""
        self.db = db.session
        self._enabled = app.config.get('CACHE_ENABLED', True)
        # Reduce memory cache size in production with many conversations
        maxsize = app.config.get('CACHE_CONTEXT_MAXSIZE', 256)
        self._memory_cache = MemoryCache(maxsize=maxsize)

    def _generate_key(self, *parts):
        """Generate a deterministic cache key from parts"""
        key_str = '|'.join(str(p) for p in parts)
        return hashlib.sha256(key_str.encode('utf-8')).hexdigest()[:64]

    def get(self, cache_key, default=None):
        """
        Get value from cache.

        Args:
            cache_key: The cache key string
            default: Value to return if key not found

        Returns:
            Cached value or default
        """
        if not self._enabled:
            return default

        # Try memory cache first (for fast context lookups)
        if hasattr(g, '_cache_memory_hit'):
            # Skip memory cache if disabled for this request (testing)
            pass
        else:
            mem_value = self._memory_cache.get(cache_key)
            if mem_value is not None:
                self._stats['hits'] += 1
                current_app.logger.debug(f"Cache HIT (memory): {cache_key[:16]}...")
                return mem_value

        # Try database cache
        try:
            now = datetime.utcnow()
            entry = CacheEntry.query.filter(
                CacheEntry.cache_key == cache_key,
                CacheEntry.expires_at > now
            ).first()

            if entry:
                value = entry.to_dict()
                self._stats['hits'] += 1
                current_app.logger.debug(f"Cache HIT (db): {cache_key[:16]}...")
                # Populate memory cache too for faster subsequent access
                self._memory_cache.set(cache_key, value, ttl_seconds=60)
                return value
            else:
                self._stats['misses'] += 1
                current_app.logger.debug(f"Cache MISS: {cache_key[:16]}...")
                return default
        except SQLAlchemyError as e:
            self._stats['db_errors'] += 1
            current_app.logger.error(f"Cache get error: {str(e)}")
            return default

    def set(self, cache_key, value, ttl_seconds):
        """
        Set value in cache with TTL.

        Args:
            cache_key: The cache key string
            value: Value to cache (must be JSON serializable)
            ttl_seconds: Time to live in seconds
        """
        if not self._enabled:
            return

        try:
            expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)
            serialized = CacheEntry.serialize(value)

            # Upsert: try to find existing entry
            entry = CacheEntry.query.filter_by(cache_key=cache_key).first()
            if entry:
                entry.cache_value = serialized
                entry.expires_at = expires_at
            else:
                entry = CacheEntry(
                    cache_key=cache_key,
                    cache_value=serialized,
                    expires_at=expires_at
                )
                db.session.add(entry)

            db.session.commit()
            self._stats['sets'] += 1

            # Also set in memory cache
            self._memory_cache.set(cache_key, value, ttl_seconds=min(ttl_seconds, 300))

            current_app.logger.debug(f"Cache SET: {cache_key[:16]}... (TTL: {ttl_seconds}s)")
        except SQLAlchemyError as e:
            db.session.rollback()
            self._stats['db_errors'] += 1
            current_app.logger.error(f"Cache set error: {str(e)}")

    def delete(self, cache_key):
        """Delete a specific cache key"""
        if not self._enabled:
            return

        try:
            entry = CacheEntry.query.filter_by(cache_key=cache_key).first()
            if entry:
                db.session.delete(entry)
                db.session.commit()
                self._stats['deletes'] += 1
                self._memory_cache.delete(cache_key)
                current_app.logger.debug(f"Cache DELETE: {cache_key[:16]}...")
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Cache delete error: {str(e)}")

    def invalidate_pattern(self, pattern_key_prefix):
        """
        Invalidate all cache keys matching a prefix.
        Useful for bulk invalidation (e.g., all file caches).
        """
        if not self._enabled:
            return

        try:
            # Find entries with key starting with pattern (use LIKE)
            entries = CacheEntry.query.filter(
                CacheEntry.cache_key.like(f"{pattern_key_prefix}%")
            ).all()

            for entry in entries:
                db.session.delete(entry)
                self._memory_cache.delete(entry.cache_key)

            db.session.commit()
            current_app.logger.info(f"Invalidated {len(entries)} cache entries with prefix: {pattern_key_prefix}")
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Cache invalidate pattern error: {str(e)}")

    def clear_all(self):
        """Clear all cache entries (admin function)"""
        if not self._enabled:
            return

        try:
            count = db.session.query(CacheEntry).delete()
            db.session.commit()
            self._memory_cache.clear()
            current_app.logger.info(f"Cleared {count} cache entries")
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Cache clear_all error: {str(e)}")

    def cleanup_expired(self):
        """
        Remove expired cache entries from database.
        Can be called periodically by a cron job.
        """
        if not self._enabled:
            return 0

        try:
            now = datetime.utcnow()
            deleted = db.session.query(CacheEntry).filter(
                CacheEntry.expires_at < now
            ).delete(synchronize_session=False)
            db.session.commit()
            if deleted > 0:
                current_app.logger.info(f"Cleaned up {deleted} expired cache entries")
            return deleted
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Cache cleanup error: {str(e)}")
            return 0

    def get_stats(self):
        """Get cache statistics (hits, misses, hit rate)"""
        total = self._stats['hits'] + self._stats['misses']
        hit_rate = (self._stats['hits'] / total * 100) if total > 0 else 0
        return {
            **self._stats,
            'total_requests': total,
            'hit_rate_percent': round(hit_rate, 2)
        }

    def reset_stats(self):
        """Reset statistics counters"""
        self._stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'db_errors': 0
        }


# Cache key generators
def generate_conversation_context_key(conversation_id, limit=15):
    """Generate cache key for conversation context"""
    return f"conv:{conversation_id}:msgs:{limit}"


def generate_ai_response_key(message, context_hash, model):
    """
    Generate cache key for AI response.

    Args:
        message: User's message (normalized)
        context_hash: SHA256 hash of conversation context
        model: AI model name

    Returns:
        Cache key string
    """
    normalized = message.strip().lower()[:200]  # Normalize and limit length
    return f"ai:resp:{model}:{context_hash}:{hashlib.sha256(normalized.encode()).hexdigest()[:16]}"


def generate_ai_stateless_key(message):
    """
    Generate cache key for stateless AI responses.
    Used for common questions that don't depend on conversation history.
    """
    normalized = message.strip().lower()[:100]
    return f"ai:stateless:{hashlib.sha256(normalized.encode()).hexdigest()[:16]}"


def generate_system_metrics_key():
    """Generate cache key for system metrics"""
    return "system:metrics"


def generate_file_content_key(filepath, mtime=None):
    """
    Generate cache key for file content.
    Includes modification time for automatic invalidation.
    """
    if mtime is None:
        import os
        try:
            mtime = str(os.path.getmtime(filepath))
        except OSError:
            mtime = "0"
    return f"file:{hashlib.sha256(filepath.encode()).hexdigest()[:16]}:mtime:{mtime}"
