from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from pathlib import Path
import json
import hashlib
import sqlite3

from cognix.utils.config import config


class MemorySystem:
    def __init__(self):
        self.short_term_memory = {}
        self._conn = self._get_connection()
        self._init_memory_tables()
        self.md_storage_path = config.home_path / "memories"
        self.md_storage_path.mkdir(parents=True, exist_ok=True)

    def _get_connection(self):
        return sqlite3.connect(config.db_path)

    def _init_memory_tables(self):
        cursor = self._conn.cursor()
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS short_term_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            confidence REAL DEFAULT 1.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS long_term_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            memory_type TEXT NOT NULL,
            key TEXT NOT NULL UNIQUE,
            value TEXT NOT NULL,
            confidence REAL DEFAULT 1.0,
            md_file_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS memory_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_memory_id INTEGER NOT NULL,
            target_memory_id INTEGER NOT NULL,
            relation_type TEXT,
            confidence REAL DEFAULT 0.8,
            FOREIGN KEY (source_memory_id) REFERENCES long_term_memory(id),
            FOREIGN KEY (target_memory_id) REFERENCES long_term_memory(id),
            UNIQUE(source_memory_id, target_memory_id)
        )
        ''')
        
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_stm_session ON short_term_memory(session_id)
        ''')
        
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_ltm_key ON long_term_memory(key)
        ''')
        
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_ltm_type ON long_term_memory(memory_type)
        ''')
        
        self._conn.commit()

    def add_short_term_memory(self, session_id: str, key: str, value: Any, expires_in_minutes: int = 1440) -> int:
        expires_at = datetime.now() + timedelta(minutes=expires_in_minutes)
        cursor = self._conn.cursor()
        cursor.execute('''
        INSERT INTO short_term_memory (session_id, key, value, expires_at)
        VALUES (?, ?, ?, ?)
        ''', (session_id, key, json.dumps(value, ensure_ascii=False), expires_at.isoformat()))
        self._conn.commit()
        return cursor.lastrowid

    def get_short_term_memory(self, session_id: str, key: str = None) -> Union[List[Dict], Dict, None]:
        cursor = self._conn.cursor()
        now = datetime.now().isoformat()
        
        if key:
            cursor.execute('''
            SELECT key, value, confidence, created_at FROM short_term_memory
            WHERE session_id = ? AND key = ? AND expires_at > ?
            ''', (session_id, key, now))
            row = cursor.fetchone()
            if row:
                return {
                    "key": row[0],
                    "value": json.loads(row[1]),
                    "confidence": row[2],
                    "created_at": row[3]
                }
            return None
        else:
            cursor.execute('''
            SELECT key, value, confidence, created_at FROM short_term_memory
            WHERE session_id = ? AND expires_at > ?
            ''', (session_id, now))
            return [
                {
                    "key": row[0],
                    "value": json.loads(row[1]),
                    "confidence": row[2],
                    "created_at": row[3]
                }
                for row in cursor.fetchall()
            ]

    def delete_short_term_memory(self, session_id: str, key: str = None):
        cursor = self._conn.cursor()
        if key:
            cursor.execute('DELETE FROM short_term_memory WHERE session_id = ? AND key = ?', (session_id, key))
        else:
            cursor.execute('DELETE FROM short_term_memory WHERE session_id = ?', (session_id,))
        self._conn.commit()

    def _generate_md_filename(self, memory_type: str, key: str) -> str:
        hash_suffix = hashlib.md5(f"{memory_type}_{key}".encode()).hexdigest()[:8]
        date_prefix = datetime.now().strftime("%Y%m%d")
        return f"{memory_type}_{date_prefix}_{hash_suffix}.md"

    def _write_memory_to_md(self, memory_type: str, key: str, value: dict) -> str:
        filename = self._generate_md_filename(memory_type, key)
        file_path = self.md_storage_path / filename
        
        md_content = f"""---
memory_type: {memory_type}
key: {key}
created_at: {datetime.now().isoformat()}
---

## {key}

{json.dumps(value, ensure_ascii=False, indent=2)}
"""
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        
        return str(file_path)

    def add_long_term_memory(self, memory_type: str, key: str, value: Any, confidence: float = 1.0) -> int:
        md_file_path = self._write_memory_to_md(memory_type, key, value if isinstance(value, dict) else {"content": value})
        
        cursor = self._conn.cursor()
        cursor.execute('''
        INSERT INTO long_term_memory (memory_type, key, value, confidence, md_file_path)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET 
            value = excluded.value, 
            confidence = excluded.confidence,
            md_file_path = excluded.md_file_path,
            updated_at = CURRENT_TIMESTAMP
        ''', (memory_type, key, json.dumps(value, ensure_ascii=False), confidence, md_file_path))
        self._conn.commit()
        
        return cursor.lastrowid

    def get_long_term_memory(self, memory_type: str = None, key: str = None) -> Union[List[Dict], Dict, None]:
        cursor = self._conn.cursor()
        
        if key:
            cursor.execute('''
            SELECT id, memory_type, key, value, confidence, md_file_path, created_at, updated_at, accessed_at
            FROM long_term_memory WHERE key = ?
            ''', (key,))
            row = cursor.fetchone()
            if row:
                cursor.execute('UPDATE long_term_memory SET accessed_at = CURRENT_TIMESTAMP WHERE id = ?', (row[0],))
                self._conn.commit()
                return {
                    "id": row[0],
                    "memory_type": row[1],
                    "key": row[2],
                    "value": json.loads(row[3]),
                    "confidence": row[4],
                    "md_file_path": row[5],
                    "created_at": row[6],
                    "updated_at": row[7],
                    "accessed_at": row[8]
                }
            return None
        else:
            if memory_type:
                cursor.execute('''
                SELECT id, memory_type, key, value, confidence, md_file_path, created_at, updated_at, accessed_at
                FROM long_term_memory WHERE memory_type = ?
                ORDER BY accessed_at DESC
                ''', (memory_type,))
            else:
                cursor.execute('''
                SELECT id, memory_type, key, value, confidence, md_file_path, created_at, updated_at, accessed_at
                FROM long_term_memory
                ORDER BY accessed_at DESC
                ''')
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    "id": row[0],
                    "memory_type": row[1],
                    "key": row[2],
                    "value": json.loads(row[3]),
                    "confidence": row[4],
                    "md_file_path": row[5],
                    "created_at": row[6],
                    "updated_at": row[7],
                    "accessed_at": row[8]
                })
                cursor.execute('UPDATE long_term_memory SET accessed_at = CURRENT_TIMESTAMP WHERE id = ?', (row[0],))
            self._conn.commit()
            
            return results

    def update_long_term_memory(self, key: str, value: Any = None, confidence: float = None):
        cursor = self._conn.cursor()
        updates = []
        params = []
        
        if value is not None:
            updates.append("value = ?")
            params.append(json.dumps(value, ensure_ascii=False))
            memory = self.get_long_term_memory(key=key)
            if memory:
                md_file_path = self._write_memory_to_md(memory["memory_type"], key, value if isinstance(value, dict) else {"content": value})
                updates.append("md_file_path = ?")
                params.append(md_file_path)
        
        if confidence is not None:
            updates.append("confidence = ?")
            params.append(confidence)
        
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(key)
        
        query = f"UPDATE long_term_memory SET {', '.join(updates)} WHERE key = ?"
        cursor.execute(query, params)
        self._conn.commit()

    def delete_long_term_memory(self, key: str) -> bool:
        memory = self.get_long_term_memory(key=key)
        if memory:
            if memory.get("md_file_path"):
                try:
                    Path(memory["md_file_path"]).unlink()
                except:
                    pass
            
            cursor = self._conn.cursor()
            cursor.execute('DELETE FROM long_term_memory WHERE key = ?', (key,))
            cursor.execute('DELETE FROM memory_links WHERE source_memory_id = ? OR target_memory_id = ?', (memory["id"], memory["id"]))
            self._conn.commit()
            return True
        return False

    def add_memory_link(self, source_key: str, target_key: str, relation_type: str = "related_to", confidence: float = 0.8):
        source_memory = self.get_long_term_memory(key=source_key)
        target_memory = self.get_long_term_memory(key=target_key)
        
        if source_memory and target_memory:
            cursor = self._conn.cursor()
            cursor.execute('''
            INSERT INTO memory_links (source_memory_id, target_memory_id, relation_type, confidence)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(source_memory_id, target_memory_id) DO UPDATE SET
                relation_type = excluded.relation_type,
                confidence = excluded.confidence
            ''', (source_memory["id"], target_memory["id"], relation_type, confidence))
            self._conn.commit()

    def get_related_memories(self, key: str, relation_type: str = None) -> List[Dict]:
        memory = self.get_long_term_memory(key=key)
        if not memory:
            return []
        
        cursor = self._conn.cursor()
        if relation_type:
            cursor.execute('''
            SELECT lt.id, lt.memory_type, lt.key, lt.value, lt.confidence
            FROM memory_links ml
            JOIN long_term_memory lt ON ml.target_memory_id = lt.id
            WHERE ml.source_memory_id = ? AND ml.relation_type = ?
            ''', (memory["id"], relation_type))
        else:
            cursor.execute('''
            SELECT lt.id, lt.memory_type, lt.key, lt.value, lt.confidence
            FROM memory_links ml
            JOIN long_term_memory lt ON ml.target_memory_id = lt.id
            WHERE ml.source_memory_id = ?
            ''', (memory["id"],))
        
        return [
            {
                "id": row[0],
                "memory_type": row[1],
                "key": row[2],
                "value": json.loads(row[3]),
                "confidence": row[4]
            }
            for row in cursor.fetchall()
        ]

    def decay_memory_confidence(self, days_threshold: int = 30, decay_rate: float = 0.1):
        cursor = self._conn.cursor()
        threshold_date = (datetime.now() - timedelta(days=days_threshold)).isoformat()
        cursor.execute('''
        UPDATE long_term_memory 
        SET confidence = MAX(0.1, confidence - ?)
        WHERE accessed_at < ? AND confidence > 0.1
        ''', (decay_rate, threshold_date))
        self._conn.commit()

    def search_memories(self, query: str, memory_type: str = None, limit: int = 10) -> List[Dict]:
        cursor = self._conn.cursor()
        query_like = f"%{query}%"
        
        if memory_type:
            cursor.execute('''
            SELECT id, memory_type, key, value, confidence, created_at, updated_at
            FROM long_term_memory 
            WHERE memory_type = ? AND (key LIKE ? OR value LIKE ?)
            ORDER BY confidence DESC, accessed_at DESC
            LIMIT ?
            ''', (memory_type, query_like, query_like, limit))
        else:
            cursor.execute('''
            SELECT id, memory_type, key, value, confidence, created_at, updated_at
            FROM long_term_memory 
            WHERE key LIKE ? OR value LIKE ?
            ORDER BY confidence DESC, accessed_at DESC
            LIMIT ?
            ''', (query_like, query_like, limit))
        
        return [
            {
                "id": row[0],
                "memory_type": row[1],
                "key": row[2],
                "value": json.loads(row[3]),
                "confidence": row[4],
                "created_at": row[5],
                "updated_at": row[6]
            }
            for row in cursor.fetchall()
        ]

    def prepare_context_for_agent(self, session_id: str, query: str = None) -> Dict:
        context = {
            "short_term": [],
            "long_term": {
                "facts": [],
                "preferences": [],
                "experiences": []
            },
            "related_memories": []
        }
        
        context["short_term"] = self.get_short_term_memory(session_id)
        
        if query:
            context["long_term"]["facts"] = self.search_memories(query, "fact", limit=5)
            context["long_term"]["preferences"] = self.search_memories(query, "preference", limit=5)
            context["long_term"]["experiences"] = self.search_memories(query, "experience", limit=5)
        else:
            context["long_term"]["facts"] = self.get_long_term_memory("fact")[:5]
            context["long_term"]["preferences"] = self.get_long_term_memory("preference")[:5]
            context["long_term"]["experiences"] = self.get_long_term_memory("experience")[:5]
        
        return context

    def record_agent_interaction(self, session_id: str, user_input: str, agent_response: str, tool_calls: List[Dict] = None):
        interaction = {
            "user_input": user_input,
            "agent_response": agent_response,
            "tool_calls": tool_calls or [],
            "timestamp": datetime.now().isoformat()
        }
        return self.add_short_term_memory(session_id, f"interaction_{datetime.now().timestamp()}", interaction)

    def import_memories(self, memories: List[Dict]):
        for memory in memories:
            self.add_long_term_memory(
                memory_type=memory.get("memory_type", "fact"),
                key=memory["key"],
                value=memory["value"],
                confidence=memory.get("confidence", 1.0)
            )

    def export_memories(self, memory_type: str = None) -> List[Dict]:
        return self.get_long_term_memory(memory_type)

    def close(self):
        self._conn.close()


_memory_system_instance = None

def get_memory_system():
    global _memory_system_instance
    if _memory_system_instance is None:
        _memory_system_instance = MemorySystem()
    return _memory_system_instance

memory_system = get_memory_system()