import sqlite3
import pandas as pd
import os

class VeriUnlearnDB:
    def __init__(self, db_path="data/audit_trail.db"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._setup_schema()

    def _setup_schema(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS granular_data 
            (id TEXT PRIMARY KEY, user TEXT, content TEXT, category TEXT, status TEXT)
        """)
        self.conn.commit()

    def add_mock_data(self):
        # Using REPLACE ensures that 'Reset' works even if records exist
        data = [
            ('Q_101', 'Rohan Kamath', 'Root Password: Sahyadri@2026', 'Security', 'ACTIVE'),
            ('Q_102', 'Rohan Kamath', 'Home: 123 Mangalore St', 'PII', 'ACTIVE'),
            ('Q_103', 'Rohan Kamath', 'Project: VeriUnlearn Pro Prototype', 'Research', 'ACTIVE')
        ]
        self.cursor.executemany("INSERT OR REPLACE INTO granular_data VALUES (?,?,?,?,?)", data)
        self.conn.commit()

    def fetch_active(self, user):
        query = "SELECT * FROM granular_data WHERE user=? AND status='ACTIVE'"
        return pd.read_sql_query(query, self.conn, params=(user,))

    def mark_purged(self, query_id):
        self.cursor.execute("UPDATE granular_data SET status='PURGED' WHERE id=?", (query_id,))
        self.conn.commit()
    def save_dynamic_query(self, query_id, user, content):
        """Saves a user prompt into the audit trail for later unlearning."""
        query = "INSERT INTO granular_data (id, user, content, category, status) VALUES (?, ?, ?, ?, ?)"
        # Marking it as 'Chat Leak' so it stands out in your project demo
        self.cursor.execute(query, (query_id, user, content, 'Chat Leak', 'ACTIVE'))
        self.conn.commit()