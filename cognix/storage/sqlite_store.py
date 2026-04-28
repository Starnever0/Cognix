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
        
        # 偏好表，新增md_hash字段用于同步校验
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            value TEXT NOT NULL,
            weight REAL DEFAULT 1.0,
            md_hash TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 规则表，新增md_hash字段用于同步校验
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            trigger TEXT NOT NULL,
            action TEXT NOT NULL,
            status TEXT DEFAULT 'pending', -- pending/active/disabled
            md_hash TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 用户习惯表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_habits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL, -- office/preference/behavior/feedback
            content TEXT UNIQUE NOT NULL,
            confidence REAL DEFAULT 0.0, -- 0-1
            occur_count INTEGER DEFAULT 1,
            first_occur_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_occur_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_verified BOOLEAN DEFAULT 0, -- 0=未确认, 1=已确认
            metadata TEXT DEFAULT '{}' -- JSON格式元数据
        )
        ''')
        
        self.conn.commit()
    
    # 偏好相关操作
    def set_preference(self, key: str, value: Dict, weight: float = 1.0, md_hash: str = ''):
        cursor = self.conn.cursor()
        cursor.execute('''
        REPLACE INTO preferences (key, value, weight, md_hash, updated_at)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (key, json.dumps(value, ensure_ascii=False), weight, md_hash))
        self.conn.commit()
    
    def get_preference(self, key: str) -> Optional[Dict]:
        cursor = self.conn.cursor()
        cursor.execute('SELECT value, weight FROM preferences WHERE key = ?', (key,))
        result = cursor.fetchone()
        return {"value": json.loads(result[0]), "weight": result[1]} if result else None
    
    def list_preferences(self) -> List[Dict]:
        cursor = self.conn.cursor()
        cursor.execute('SELECT key, value, weight, created_at, updated_at, md_hash FROM preferences')
        return [
            {
                "key": row[0], 
                "value": json.loads(row[1]), 
                "weight": row[2],
                "created_at": row[3],
                "updated_at": row[4],
                "md_hash": row[5]
            } 
            for row in cursor.fetchall()
        ]
    
    def delete_preference(self, key: str):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM preferences WHERE key = ?', (key,))
        self.conn.commit()
    
    # 规则相关操作
    def add_rule(self, name: str, trigger: str, action: Dict, status: str = 'pending', md_hash: str = '') -> int:
        cursor = self.conn.cursor()
        cursor.execute('''
        INSERT INTO rules (name, trigger, action, status, md_hash)
        VALUES (?, ?, ?, ?, ?)
        ''', (name, trigger, json.dumps(action, ensure_ascii=False), status, md_hash))
        self.conn.commit()
        return cursor.lastrowid
    
    def update_rule_status(self, rule_id: int, status: str, md_hash: str = ''):
        cursor = self.conn.cursor()
        cursor.execute('''
        UPDATE rules SET status = ?, md_hash = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        ''', (status, md_hash, rule_id))
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
            cursor.execute('SELECT id, name, trigger, action, status, created_at, updated_at, md_hash FROM rules WHERE status = ?', (status,))
        else:
            cursor.execute('SELECT id, name, trigger, action, status, created_at, updated_at, md_hash FROM rules')
        return [
            {
                "id": row[0], 
                "name": row[1], 
                "trigger": row[2], 
                "action": json.loads(row[3]), 
                "status": row[4],
                "created_at": row[5],
                "updated_at": row[6],
                "md_hash": row[7]
            } 
            for row in cursor.fetchall()
        ]
    
    def get_rule(self, rule_id: int) -> Optional[Dict]:
        cursor = self.conn.cursor()
        cursor.execute('SELECT id, name, trigger, action, status, md_hash FROM rules WHERE id = ?', (rule_id,))
        row = cursor.fetchone()
        if row:
            return {
                "id": row[0], 
                "name": row[1], 
                "trigger": row[2], 
                "action": json.loads(row[3]), 
                "status": row[4],
                "md_hash": row[5]
            }
        return None
    
    # 用户习惯相关操作
    def add_habit(self, category: str, content: str, confidence: float = 0.0, 
                  occur_count: int = 1, metadata: Dict = None) -> int:
        """添加或更新用户习惯"""
        cursor = self.conn.cursor()
        metadata = metadata or {}
        
        # 先检查是否已存在相同内容的习惯
        cursor.execute('SELECT id, occur_count, confidence FROM user_habits WHERE content = ?', (content,))
        existing = cursor.fetchone()
        
        if existing:
            habit_id, old_count, old_confidence = existing
            new_count = old_count + occur_count
            # 置信度随着出现次数增加而提高，最高0.95
            new_confidence = min(old_confidence + (0.1 * occur_count), 0.95)
            
            cursor.execute('''
            UPDATE user_habits 
            SET occur_count = ?, confidence = ?, last_occur_time = CURRENT_TIMESTAMP, metadata = ?
            WHERE id = ?
            ''', (new_count, new_confidence, json.dumps(metadata, ensure_ascii=False), habit_id))
            self.conn.commit()
            return habit_id
        else:
            cursor.execute('''
            INSERT INTO user_habits (category, content, confidence, occur_count, metadata)
            VALUES (?, ?, ?, ?, ?)
            ''', (category, content, confidence, occur_count, json.dumps(metadata, ensure_ascii=False)))
            self.conn.commit()
            return cursor.lastrowid
    
    def get_habits(self, category: str = None, min_confidence: float = 0.0, 
                   min_occur_count: int = 1, only_verified: bool = False) -> List[Dict]:
        """查询用户习惯"""
        cursor = self.conn.cursor()
        conditions = []
        params = []
        
        if category:
            conditions.append("category = ?")
            params.append(category)
        if min_confidence > 0:
            conditions.append("confidence >= ?")
            params.append(min_confidence)
        if min_occur_count > 1:
            conditions.append("occur_count >= ?")
            params.append(min_occur_count)
        if only_verified:
            conditions.append("is_verified = 1")
        
        query = '''
        SELECT id, category, content, confidence, occur_count, 
               first_occur_time, last_occur_time, is_verified, metadata
        FROM user_habits
        '''
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY confidence DESC, occur_count DESC"
        
        cursor.execute(query, params)
        return [
            {
                "id": row[0],
                "category": row[1],
                "content": row[2],
                "confidence": row[3],
                "occur_count": row[4],
                "first_occur_time": row[5],
                "last_occur_time": row[6],
                "is_verified": bool(row[7]),
                "metadata": json.loads(row[8])
            }
            for row in cursor.fetchall()
        ]
    
    def mark_habit_verified(self, habit_id: int, verified: bool = True) -> bool:
        """标记习惯为已确认"""
        cursor = self.conn.cursor()
        cursor.execute('''
        UPDATE user_habits SET is_verified = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?
        ''', (1 if verified else 0, habit_id))
        self.conn.commit()
        return cursor.rowcount > 0
    
    def delete_habit(self, habit_id: int) -> bool:
        """删除习惯"""
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM user_habits WHERE id = ?', (habit_id,))
        self.conn.commit()
        return cursor.rowcount > 0
    
    def close(self):
        self.conn.close()

sqlite_store = SQLiteStore()
