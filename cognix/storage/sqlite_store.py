import sqlite3
from typing import Dict, List, Optional
from cognix.utils.config import config
import json
from datetime import datetime

class SQLiteStore:
    def __init__(self):
        self.conn = sqlite3.connect(config.db_path)
        self._init_tables()
    
    def _init_tables(self):
        cursor = self.conn.cursor()
        
        # 偏好表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            value TEXT NOT NULL,
            weight REAL DEFAULT 1.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 规则表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            trigger TEXT NOT NULL,
            action TEXT NOT NULL,
            status TEXT DEFAULT 'pending', -- pending/active/disabled
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        self.conn.commit()
    
    # 偏好相关操作
    def set_preference(self, key: str, value: Dict, weight: float = 1.0):
        cursor = self.conn.cursor()
        cursor.execute('''
        REPLACE INTO preferences (key, value, weight, updated_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ''', (key, json.dumps(value, ensure_ascii=False), weight))
        self.conn.commit()
    
    def get_preference(self, key: str) -> Optional[Dict]:
        cursor = self.conn.cursor()
        cursor.execute('SELECT value FROM preferences WHERE key = ?', (key,))
        result = cursor.fetchone()
        return json.loads(result[0]) if result else None
    
    def list_preferences(self) -> List[Dict]:
        cursor = self.conn.cursor()
        cursor.execute('SELECT key, value, weight, created_at, updated_at FROM preferences')
        return [
            {
                "key": row[0], 
                "value": json.loads(row[1]), 
                "weight": row[2],
                "created_at": row[3],
                "updated_at": row[4]
            } 
            for row in cursor.fetchall()
        ]
    
    def delete_preference(self, key: str):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM preferences WHERE key = ?', (key,))
        self.conn.commit()
    
    # 规则相关操作
    def add_rule(self, name: str, trigger: str, action: Dict, status: str = 'pending') -> int:
        cursor = self.conn.cursor()
        cursor.execute('''
        INSERT INTO rules (name, trigger, action, status)
        VALUES (?, ?, ?, ?)
        ''', (name, trigger, json.dumps(action, ensure_ascii=False), status))
        self.conn.commit()
        return cursor.lastrowid
    
    def update_rule_status(self, rule_id: int, status: str):
        cursor = self.conn.cursor()
        cursor.execute('''
        UPDATE rules SET status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        ''', (status, rule_id))
        self.conn.commit()
    
    def update_rule(self, rule_id: int, **kwargs):
        cursor = self.conn.cursor()
        set_clause = []
        params = []
        for key, value in kwargs.items():
            if key == 'action':
                value = json.dumps(value, ensure_ascii=False)
            set_clause.append(f"{key} = ?")
            params.append(value)
        
        params.append(rule_id)
        query = f"UPDATE rules SET {', '.join(set_clause)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
        cursor.execute(query, params)
        self.conn.commit()
    
    def list_rules(self, status: Optional[str] = None) -> List[Dict]:
        cursor = self.conn.cursor()
        if status:
            cursor.execute('SELECT id, name, trigger, action, status, created_at, updated_at FROM rules WHERE status = ?', (status,))
        else:
            cursor.execute('SELECT id, name, trigger, action, status, created_at, updated_at FROM rules')
        return [
            {
                "id": row[0], 
                "name": row[1], 
                "trigger": row[2], 
                "action": json.loads(row[3]), 
                "status": row[4],
                "created_at": row[5],
                "updated_at": row[6]
            } 
            for row in cursor.fetchall()
        ]
    
    def get_rule(self, rule_id: int) -> Optional[Dict]:
        cursor = self.conn.cursor()
        cursor.execute('SELECT id, name, trigger, action, status FROM rules WHERE id = ?', (rule_id,))
        row = cursor.fetchone()
        if row:
            return {
                "id": row[0], 
                "name": row[1], 
                "trigger": row[2], 
                "action": json.loads(row[3]), 
                "status": row[4]
            }
        return None
    
    def close(self):
        self.conn.close()

sqlite_store = SQLiteStore()
