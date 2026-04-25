from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path
import hashlib
import sqlite3
import uuid

from cognix.utils.config import config


class MarkdownMemory:
    """Markdown文件格式记忆系统 - Markdown是真实来源，SQLite是索引"""
    
    def __init__(self):
        self._conn = self._get_connection()
        self._init_tables()
        
        # 创建目录结构
        self.memory_dir = config.home_path / "memory"
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        
        self.sessions_dir = config.home_path / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        
        # 短期记忆（会话级）
        self.short_term_memory: Dict[str, List[Dict]] = {}
    
    def _get_connection(self):
        return sqlite3.connect(config.db_path)
    
    def _init_tables(self):
        cursor = self._conn.cursor()
        
        # 文件元数据表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS files (
            path TEXT PRIMARY KEY,
            source TEXT NOT NULL DEFAULT 'memory',
            hash TEXT NOT NULL,
            updated_at INTEGER NOT NULL
        )
        ''')
        
        # 记忆块表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS chunks (
            id TEXT PRIMARY KEY,
            path TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'memory',
            start_line INTEGER NOT NULL,
            end_line INTEGER NOT NULL,
            hash TEXT NOT NULL,
            text TEXT NOT NULL,
            updated_at INTEGER NOT NULL
        )
        ''')
        
        # 全文搜索索引（FTS5）
        cursor.execute('''
        CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
            text,
            id UNINDEXED,
            path UNINDEXED,
            source UNINDEXED
        )
        ''')
        
        # 索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_chunks_path ON chunks(path)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_chunks_source ON chunks(source)')
        
        self._conn.commit()
    
    def _compute_hash(self, text: str) -> str:
        """计算内容的SHA256哈希"""
        return hashlib.sha256(text.encode('utf-8')).hexdigest()
    
    def _get_daily_md_path(self, date: Optional[datetime] = None) -> Path:
        """获取每日记忆文件路径"""
        if date is None:
            date = datetime.now()
        return self.memory_dir / f"{date.strftime('%Y-%m-%d')}.md"
    
    def _ensure_daily_md(self, date: Optional[datetime] = None) -> Path:
        """确保每日记忆文件存在"""
        file_path = self._get_daily_md_path(date)
        if not file_path.exists():
            content = f"# {datetime.now().strftime('%Y-%m-%d')} 日志\n\n"
            file_path.write_text(content, encoding='utf-8')
        return file_path
    
    def _parse_markdown_chunks(self, file_path: Path) -> List[Dict]:
        """解析Markdown文件为记忆块"""
        if not file_path.exists():
            return []
        
        lines = file_path.read_text(encoding='utf-8').split('\n')
        chunks = []
        current_heading = None
        current_lines = []
        current_start_line = 0
        
        for line_num, line in enumerate(lines):
            # 检测标题行（## 开始）
            if line.startswith('## '):
                # 保存之前的块
                if current_heading and current_lines:
                    chunk_text = '\n'.join(current_lines)
                    chunks.append({
                        'heading': current_heading,
                        'text': chunk_text,
                        'start_line': current_start_line,
                        'end_line': line_num - 1
                    })
                
                # 开始新块
                current_heading = line[3:].strip()
                current_lines = [line]
                current_start_line = line_num + 1  # 行号从1开始
            elif current_heading is not None:
                current_lines.append(line)
        
        # 保存最后一个块
        if current_heading and current_lines:
            chunk_text = '\n'.join(current_lines)
            chunks.append({
                'heading': current_heading,
                'text': chunk_text,
                'start_line': current_start_line,
                'end_line': len(lines)
            })
        
        return chunks
    
    def _index_markdown_file(self, file_path: Path, source: str = "memory"):
        """索引单个Markdown文件"""
        if not file_path.exists():
            return
        
        content = file_path.read_text(encoding='utf-8')
        file_hash = self._compute_hash(content)
        file_mtime = int(file_path.stat().st_mtime * 1000)
        file_str = str(file_path.absolute())
        
        cursor = self._conn.cursor()
        
        # 检查文件是否已更新
        cursor.execute('SELECT hash FROM files WHERE path = ?', (file_str,))
        row = cursor.fetchone()
        
        if row and row[0] == file_hash:
            return  # 未变化，无需重新索引
        
        # 删除旧索引
        cursor.execute('DELETE FROM chunks WHERE path = ?', (file_str,))
        
        # 解析新块
        chunks = self._parse_markdown_chunks(file_path)
        
        for chunk in chunks:
            chunk_id = str(uuid.uuid4())
            chunk_hash = self._compute_hash(chunk['text'])
            
            # 插入chunks表
            cursor.execute('''
                INSERT INTO chunks (id, path, source, start_line, end_line, hash, text, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (chunk_id, file_str, source, chunk['start_line'], chunk['end_line'], 
                  chunk_hash, chunk['text'], file_mtime))
            
            # 插入FTS索引
            try:
                cursor.execute('''
                    INSERT INTO chunks_fts (text, id, path, source)
                    VALUES (?, ?, ?, ?)
                ''', (chunk['text'], chunk_id, file_str, source))
            except Exception:
                # FTS索引可能有问题，跳过
                pass
        
        # 更新文件元数据
        cursor.execute('''
            INSERT OR REPLACE INTO files (path, source, hash, updated_at)
            VALUES (?, ?, ?, ?)
        ''', (file_str, source, file_hash, file_mtime))
        
        self._conn.commit()
    
    def _index_all_memory_files(self):
        """索引所有记忆文件"""
        # 索引每日日志
        for md_file in self.memory_dir.glob("*.md"):
            self._index_markdown_file(md_file, "memory")
        
        # 索引MEMORY.md（如果存在）
        memory_md = config.home_path / "MEMORY.md"
        if memory_md.exists():
            self._index_markdown_file(memory_md, "persistent")
    
    def _append_to_markdown(self, file_path: Path, heading: str, content: str):
        """向Markdown文件追加内容"""
        if not file_path.exists():
            md_content = f"# {datetime.now().strftime('%Y-%m-%d')} 日志\n\n"
            file_path.write_text(md_content, encoding='utf-8')
        
        md_content = file_path.read_text(encoding='utf-8')
        
        # 检查是否已有该标题
        heading_line = f"## {heading}"
        if heading_line in md_content:
            # 追加到现有标题下
            before_heading, after_heading = md_content.split(heading_line, 1)
            new_content = before_heading + heading_line + '\n' + content + '\n' + after_heading
        else:
            # 添加新标题
            new_content = md_content + f"\n## {heading}\n\n{content}\n"
        
        file_path.write_text(new_content, encoding='utf-8')
        self._index_markdown_file(file_path, "memory")
    
    def add_memory(self, heading: str, content: str, date: Optional[datetime] = None):
        """添加记忆到每日日志"""
        file_path = self._ensure_daily_md(date)
        self._append_to_markdown(file_path, heading, content)
    
    def add_persistent_memory(self, heading: str, content: str):
        """添加持久记忆到MEMORY.md"""
        memory_md = config.home_path / "MEMORY.md"
        # 确保文件有合适的标题
        if not memory_md.exists():
            memory_md.write_text("# 持久记忆\n\n", encoding='utf-8')
        self._append_to_markdown(memory_md, heading, content)
    
    def search_memory(self, query: str, limit: int = 10, source: Optional[str] = None) -> List[Dict]:
        """搜索记忆 - 优先使用FTS5全文搜索"""
        self._index_all_memory_files()  # 确保索引最新
        
        cursor = self._conn.cursor()
        
        # 改进搜索策略：先尝试FTS，失败后使用LIKE回退
        results = []
        
        try:
            # 方法1：使用FTS全文搜索
            if source:
                cursor.execute('''
                    SELECT c.id, c.path, c.source, c.start_line, c.end_line, c.text
                    FROM chunks_fts fts
                    JOIN chunks c ON fts.id = c.id
                    WHERE chunks_fts MATCH ? AND c.source = ?
                    LIMIT ?
                ''', (query, source, limit))
            else:
                cursor.execute('''
                    SELECT c.id, c.path, c.source, c.start_line, c.end_line, c.text
                    FROM chunks_fts fts
                    JOIN chunks c ON fts.id = c.id
                    WHERE chunks_fts MATCH ?
                    LIMIT ?
                ''', (query, limit))
            
            rows = cursor.fetchall()
            
            for row in rows:
                results.append({
                    'id': row[0],
                    'path': row[1],
                    'source': row[2],
                    'start_line': row[3],
                    'end_line': row[4],
                    'text': row[5],
                    'score': 1.0
                })
        
        except Exception as e:
            # 如果FTS搜索出错，尝试直接从Markdown文件读取
            pass
        
        # 如果没有结果，尝试直接读取Markdown文件搜索
        if not results:
            results = self._fallback_search(query, source, limit)
        
        return results
    
    def _fallback_search(self, query: str, source: Optional[str], limit: int) -> List[Dict]:
        """回退搜索：直接读取Markdown文件搜索"""
        results = []
        query_lower = query.lower()
        
        # 搜索每日记忆
        for md_file in self.memory_dir.glob("*.md"):
            if source and source != 'memory':
                continue
            
            content = md_file.read_text(encoding='utf-8')
            if query_lower in content.lower():
                results.append({
                    'id': str(hash(str(md_file))),
                    'path': str(md_file),
                    'source': 'memory',
                    'start_line': 1,
                    'end_line': len(content.split('\n')),
                    'text': content,
                    'score': 0.8
                })
                if len(results) >= limit:
                    break
        
        # 搜索持久记忆
        if len(results) < limit:
            memory_md = self.memory_dir.parent / "MEMORY.md"
            if memory_md.exists() and (source is None or source == 'persistent'):
                content = memory_md.read_text(encoding='utf-8')
                if query_lower in content.lower():
                    results.append({
                        'id': str(hash(str(memory_md))),
                        'path': str(memory_md),
                        'source': 'persistent',
                        'start_line': 1,
                        'end_line': len(content.split('\n')),
                        'text': content,
                        'score': 0.9
                    })
        
        return results[:limit]
    
    def read_memory_file(self, file_path: Path, start_line: Optional[int] = None, 
                        end_line: Optional[int] = None) -> str:
        """读取记忆文件内容"""
        if not file_path.exists():
            return ""
        
        lines = file_path.read_text(encoding='utf-8').split('\n')
        
        if start_line is None:
            start_line = 1
        if end_line is None:
            end_line = len(lines)
        
        # 调整为0基索引
        start_idx = max(0, start_line - 1)
        end_idx = min(len(lines), end_line)
        
        return '\n'.join(lines[start_idx:end_idx])
    
    def get_daily_context(self, days_back: int = 1) -> str:
        """获取最近几天的上下文"""
        context_parts = []
        today = datetime.now()
        
        for i in range(days_back, -1, -1):
            date = today - timedelta(days=i)
            file_path = self._get_daily_md_path(date)
            if file_path.exists():
                content = self.read_memory_file(file_path)
                if content.strip():
                    context_parts.append(f"## {date.strftime('%Y-%m-%d')}\n{content}")
        
        # 加入MEMORY.md
        memory_md = config.home_path / "MEMORY.md"
        if memory_md.exists():
            content = self.read_memory_file(memory_md)
            if content.strip():
                context_parts.append(f"## 持久记忆\n{content}")
        
        return '\n\n'.join(context_parts)
    
    def add_short_term(self, session_id: str, key: str, value: Any):
        """添加短期记忆"""
        if session_id not in self.short_term_memory:
            self.short_term_memory[session_id] = []
        
        self.short_term_memory[session_id].append({
            'key': key,
            'value': value,
            'timestamp': datetime.now().isoformat()
        })
    
    def get_short_term(self, session_id: str) -> List[Dict]:
        """获取短期记忆"""
        return self.short_term_memory.get(session_id, [])
    
    def clear_short_term(self, session_id: str):
        """清除短期记忆"""
        if session_id in self.short_term_memory:
            del self.short_term_memory[session_id]
    
    def rebuild_index(self):
        """重建索引"""
        cursor = self._conn.cursor()
        cursor.execute('DELETE FROM files')
        cursor.execute('DELETE FROM chunks')
        cursor.execute('DELETE FROM chunks_fts')
        self._conn.commit()
        self._index_all_memory_files()
    
    def close(self):
        self._conn.close()


_memory_instance = None


def get_memory_system() -> MarkdownMemory:
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = MarkdownMemory()
    return _memory_instance


# 延迟创建，避免导入时就初始化
memory_system = None
