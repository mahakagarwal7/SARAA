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
