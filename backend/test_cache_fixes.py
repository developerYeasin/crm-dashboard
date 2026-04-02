#!/usr/bin/env python3
"""
Test script to verify:
1. Database indexes are present
2. Conversation context caching works
3. Cache invalidation works
"""

import os
import sys
sys.path.insert(0, '.')

from dotenv import load_dotenv
load_dotenv()

from flask import Flask
from extensions import db
from cache import Cache, generate_conversation_context_key
from models import AIMessage, AIConversation
from sqlalchemy import text
import time

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{int(os.getenv('DB_PORT', 3306))}/{os.getenv('DB_NAME')}"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['CACHE_ENABLED'] = True
    app.config['CACHE_TTL_CONTEXT'] = 30
    db.init_app(app)
    cache = Cache(app)
    app.cache = cache
    return app

def test_indexes(app):
    print("\n=== Testing Database Indexes ===")
    with app.app_context():
        inspector = db.inspect(db.engine)
        indexes = inspector.get_indexes('ai_messages')
        index_names = [idx['name'] for idx in indexes]
        expected = ['idx_ai_messages_conversation_id', 'idx_ai_messages_conversation_timestamp']
        for name in expected:
            if name in index_names:
                print(f"✓ Index exists: {name}")
            else:
                print(f"✗ Missing index: {name}")
                return False
    return True

def test_context_caching(app):
    print("\n=== Testing Conversation Context Caching ===")
    with app.app_context():
        # Use a test conversation ID (we'll use 99999, which likely has no messages)
        test_conv_id = 99999
        limit = 15
        cache_key = generate_conversation_context_key(test_conv_id, limit)

        # Ensure cache is clean
        app.cache.delete(cache_key)

        # First call should be a cache miss and query DB
        start = time.time()
        context1 = app.cache.get(cache_key)
        if context1 is not None:
            print("✗ Expected cache miss, but got cached value")
            return False
        db_time1 = time.time() - start
        print(f"Cache miss as expected (took {db_time1:.4f}s)")

        # Simulate storing something in cache (normally get_conversation_context does this)
        empty_context = []
        app.cache.set(cache_key, empty_context, ttl_seconds=30)

        # Second call should be a cache hit
        start = time.time()
        context2 = app.cache.get(cache_key)
        if context2 is None:
            print("✗ Expected cache hit, but got miss")
            return False
        db_time2 = time.time() - start
        print(f"✓ Cache hit (took {db_time2:.4f}s)")

        # Invalidate the cache
        app.cache.delete(cache_key)
        context3 = app.cache.get(cache_key)
        if context3 is not None:
            print("✗ Invalidation failed")
            return False
        print("✓ Invalidation works")
        return True

def test_pattern_invalidation(app):
    print("\n=== Testing Pattern Invalidation ===")
    with app.app_context():
        test_conv_id = 88888
        # Create multiple keys with same prefix
        keys = [
            f"conv:{test_conv_id}:msgs:15",
            f"conv:{test_conv_id}:msgs:30",
            f"conv:{test_conv_id}:other"
        ]
        for key in keys:
            app.cache.set(key, {"test": True}, ttl_seconds=60)

        # Verify they are set
        for key in keys:
            if app.cache.get(key) is None:
                print(f"✗ Key {key} not found after set")
                return False
        print(f"✓ Set {len(keys)} test keys")

        # Invalidate by pattern
        deleted = app.cache.invalidate_pattern(f"conv:{test_conv_id}:")
        print(f"Invalidated {deleted} entries with pattern conv:{test_conv_id}:")

        # Check they are gone
        for key in keys:
            if app.cache.get(key) is not None:
                print(f"✗ Key {key} still exists after invalidate")
                return False
        print("✓ Pattern invalidation works")
        return True

def main():
    print("Starting cache and database tests...")
    app = create_app()

    success = True
    success = test_indexes(app) and success
    success = test_context_caching(app) and success
    success = test_pattern_invalidation(app) and success

    if success:
        print("\n✅ All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)

if __name__ == '__main__':
    main()
