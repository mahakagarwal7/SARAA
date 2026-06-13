import sqlite3
import os
from datetime import datetime
from typing import Dict, List
from contextlib import closing

class MemoryDB:
    """A lightweight SQLite memory store acting as a stand-in for Azure Cosmos DB."""
    
    def __init__(self, db_name="memory.db"):
        # Store in the backend directory
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.db_path = os.path.join(base_dir, db_name)
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with closing(self._get_connection()) as conn:
            with conn:
                cursor = conn.cursor()
                # Table for Users
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id TEXT PRIMARY KEY,
                        username TEXT UNIQUE,
                        password_hash TEXT
                    )
                ''')
                # Table for Threads
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS threads (
                        id TEXT PRIMARY KEY,
                        user_id TEXT,
                        title TEXT,
                        created_at TIMESTAMP,
                        updated_at TIMESTAMP
                    )
                ''')
                # Table for Messages
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        thread_id TEXT,
                        role TEXT,
                        content TEXT,
                        execution_log TEXT,
                        created_at TIMESTAMP
                    )
                ''')
                # Table for User Preferences
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS preferences (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT,
                        key TEXT,
                        value TEXT,
                        updated_at TIMESTAMP
                    )
                ''')
                # Table for Briefing History
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS briefings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        subject TEXT,
                        content TEXT,
                        created_at TIMESTAMP
                    )
                ''')

    def save_preference(self, user_id: str, key: str, value: str):
        with closing(self._get_connection()) as conn:
            with conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO preferences (user_id, key, value, updated_at)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, key, value, datetime.now()))

    def get_preferences(self, user_id: str) -> Dict[str, str]:
        with closing(self._get_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT key, value FROM preferences WHERE user_id = ? ORDER BY id DESC', (user_id,))
            rows = cursor.fetchall()
            
            # Keep the latest value for each key
            prefs = {}
            for key, value in rows:
                if key not in prefs:
                    prefs[key] = value
            return prefs

    def save_briefing(self, subject: str, content: str):
        with closing(self._get_connection()) as conn:
            with conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO briefings (subject, content, created_at)
                    VALUES (?, ?, ?)
                ''', (subject, content, datetime.now()))

    def get_past_briefings(self, limit: int = 3) -> List[Dict[str, str]]:
        with closing(self._get_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT subject, created_at FROM briefings ORDER BY id DESC LIMIT ?', (limit,))
            return [{"subject": row[0], "created_at": row[1]} for row in cursor.fetchall()]

    # --- Users ---
    def create_user(self, user_id: str, username: str, password_hash: str):
        with closing(self._get_connection()) as conn:
            with conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO users (id, username, password_hash)
                    VALUES (?, ?, ?)
                ''', (user_id, username, password_hash))

    def get_user_by_username(self, username: str):
        with closing(self._get_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, username, password_hash FROM users WHERE username = ?', (username,))
            row = cursor.fetchone()
            if row:
                return {"id": row[0], "username": row[1], "password_hash": row[2]}
            return None

    # --- Threads ---
    def create_thread(self, thread_id: str, user_id: str, title: str):
        with closing(self._get_connection()) as conn:
            with conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO threads (id, user_id, title, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (thread_id, user_id, title, datetime.now(), datetime.now()))

    def get_user_threads(self, user_id: str) -> List[Dict]:
        with closing(self._get_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, title, created_at, updated_at FROM threads WHERE user_id = ? ORDER BY updated_at DESC', (user_id,))
            return [{"id": row[0], "title": row[1], "created_at": row[2], "updated_at": row[3]} for row in cursor.fetchall()]

    def update_thread_updated_at(self, thread_id: str):
        with closing(self._get_connection()) as conn:
            with conn:
                cursor = conn.cursor()
                cursor.execute('UPDATE threads SET updated_at = ? WHERE id = ?', (datetime.now(), thread_id))

    # --- Messages ---
    def add_message(self, thread_id: str, role: str, content: str, execution_log: str = None):
        with closing(self._get_connection()) as conn:
            with conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO messages (thread_id, role, content, execution_log, created_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (thread_id, role, content, execution_log, datetime.now()))
        self.update_thread_updated_at(thread_id)

    def get_thread_messages(self, thread_id: str) -> List[Dict]:
        with closing(self._get_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, role, content, execution_log, created_at FROM messages WHERE thread_id = ? ORDER BY id ASC', (thread_id,))
            return [{"id": row[0], "role": row[1], "content": row[2], "execution_log": row[3], "created_at": row[4]} for row in cursor.fetchall()]
