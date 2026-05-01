from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import hashlib
import sqlite3
import uuid

from cognix.utils.config import config
from .memory_classifier import MemoryClassifier


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
        
        # 分类记忆管理器
        self.classifier = MemoryClassifier(self.memory_dir)
        
        # 内存缓存（懒加载+预热）
        self._memory_cache = {}  # 分类记忆缓存：{category: (content, mtime)}
        self._cache_enabled = True
        self._last_index_time = 0  # 上次索引时间，避免频繁索引
        
        # 启动时预热高频缓存
        self._warmup_cache()
    
    def _get_connection(self):
        return sqlite3.connect(config.db_path)
    
    def _warmup_cache(self):
        """预热高频缓存，系统启动时加载核心记忆到内存"""
        if not self._cache_enabled:
            return
        
        # 预热高频分类：user/settings/office，这三类读取最频繁
        high_frequency_categories = ["user", "settings", "office"]
        for category in high_frequency_categories:
            try:
                file_path = self.classifier.get_category_path(category)
                if file_path.exists():
                    content = file_path.read_text(encoding='utf-8')
                    mtime = int(file_path.stat().st_mtime * 1000)
                    self._memory_cache[category] = (content, mtime)
            except Exception:
                # 预热失败不影响正常功能
                pass
    
    def _get_cached_memory(self, category: str) -> Optional[str]:
        """获取缓存的分类记忆，过时自动刷新"""
        if not self._cache_enabled or category not in self._memory_cache:
            return None
        
        cached_content, cached_mtime = self._memory_cache[category]
        file_path = self.classifier.get_category_path(category)
        
        if not file_path.exists():
            return None
        
        current_mtime = int(file_path.stat().st_mtime * 1000)
        if current_mtime == cached_mtime:
            return cached_content
        
        # 文件已更新，删除缓存
        del self._memory_cache[category]
        return None
    
    def _update_cache(self, category: str, content: str, mtime: int):
        """更新缓存"""
        if self._cache_enabled:
            self._memory_cache[category] = (content, mtime)
    
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
        
        # ===================== 结构化缓存表 =====================
        # 用户偏好缓存表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS cached_preferences (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            source_path TEXT NOT NULL,
            confidence REAL NOT NULL DEFAULT 1.0,
            updated_at INTEGER NOT NULL,
            extracted_at INTEGER NOT NULL
        )
        ''')
        
        # 实体缓存表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS cached_entities (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            type TEXT NOT NULL, -- person/place/thing/skill/document
            content TEXT NOT NULL,
            summary TEXT,
            source_path TEXT NOT NULL,
            confidence REAL NOT NULL DEFAULT 0.8,
            updated_at INTEGER NOT NULL,
            extracted_at INTEGER NOT NULL
        )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_entities_name ON cached_entities(name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_entities_type ON cached_entities(type)')
        
        # 习惯缓存表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS cached_habits (
            id TEXT PRIMARY KEY,
            pattern TEXT NOT NULL, -- 习惯模式
            type TEXT NOT NULL, -- timing/operation/preference
            description TEXT NOT NULL,
            frequency INTEGER NOT NULL DEFAULT 1, -- 出现次数
            confidence REAL NOT NULL DEFAULT 0.7,
            last_occurrence_at INTEGER NOT NULL,
            extracted_at INTEGER NOT NULL
        )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_habits_type ON cached_habits(type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_habits_frequency ON cached_habits(frequency)')
        
        # ===================== 实体关系表 =====================
        # 实体表（对应memU的Memory Items）
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS entities (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            type TEXT NOT NULL, -- person/organization/document/skill/task/concept/other
            content TEXT NOT NULL, -- 完整内容
            summary TEXT, -- 摘要（用于默认返回）
            source_path TEXT NOT NULL, -- 来源Markdown文件路径
            confidence REAL NOT NULL DEFAULT 0.8,
            updated_at INTEGER NOT NULL,
            extracted_at INTEGER NOT NULL
        )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_entities_source ON entities(source_path)')
        
        # 实体关系表（对应memU的Cross-references软链接）
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS entity_relations (
            id TEXT PRIMARY KEY,
            from_entity_id TEXT NOT NULL,
            to_entity_id TEXT NOT NULL,
            relation_type TEXT NOT NULL, -- 关联类型：belongs_to/used_for/related_to/owned_by/contains/depends_on
            confidence REAL NOT NULL DEFAULT 0.7,
            source_path TEXT NOT NULL, -- 关系来源文件
            created_at INTEGER NOT NULL
        )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_relations_from ON entity_relations(from_entity_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_relations_to ON entity_relations(to_entity_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_relations_type ON entity_relations(relation_type)')
        
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
        
        # 删除旧索引和对应缓存
        cursor.execute('DELETE FROM chunks WHERE path = ?', (file_str,))
        self.invalidate_cache_by_path(file_str)
        
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
    
    def _index_all_memory_files(self, force: bool = False):
        """索引所有记忆文件
        :param force: 是否强制重新索引，默认false，有1秒防抖动
        """
        import time
        current_time = time.time()
        if not force and current_time - self._last_index_time < 1.0:
            return  # 1秒内不重复索引
        
        self._last_index_time = current_time
        
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
    
    def add_classified_memory(self, category: str, heading: str, content: str) -> None:
        """
        添加分类记忆
        :param category: 分类：user/settings/office/feedback/reference
        :param heading: 记忆标题
        :param content: 记忆内容
        """
        self.classifier.add_memory(category, heading, content)
        # 索引新添加的内容
        file_path = self.classifier.get_category_path(category)
        self._index_markdown_file(file_path, "memory")
    
    def _rule_classify(self, content_lower: str) -> Tuple[str, float]:
        """
        规则分类，返回分类结果和置信度
        :return: (category, confidence)
        """
        # 分类关键词配置（强匹配关键词权重2，弱匹配权重1）
        category_keywords = {
            "user": [
                # 强匹配
                ("我是", 2), ("我的", 2), ("叫我", 2), ("姓名", 2), ("职位", 2), ("角色", 2),
                ("称呼", 2), ("联系方式", 2), ("邮箱", 2), ("电话", 2), ("微信", 2), ("钉钉", 2),
                # 弱匹配
                ("我在", 1), ("我负责", 1), ("我的工作", 1), ("我平时", 1), ("大家叫我", 1),
                ("我的名字", 1), ("岗位是", 1), ("工号", 1), ("部门", 1), ("团队", 1)
            ],
            "settings": [
                # 强匹配
                ("偏好", 2), ("默认", 2), ("设置", 2), ("格式", 2), ("我习惯", 2), ("我喜欢", 2),
                ("总是", 2), ("永远", 2), ("输出风格", 2), ("语言", 2), ("用什么格式", 2),
                ("不要用", 2), ("要用", 2),
                # 弱匹配
                ("视图", 1), ("通知", 1), ("模板", 1), ("展示", 1), ("显示", 1), ("模式", 1),
                ("静音", 1), ("提醒方式", 1), ("回复风格", 1), ("字数", 1), ("简洁", 1), ("详细", 1)
            ],
            "office": [
                # 强匹配
                ("周报", 2), ("月报", 2), ("日报", 2), ("会议", 2), ("开会", 2), ("审批", 2),
                ("报销", 2), ("出差", 2), ("发送给", 2), ("发给", 2), ("抄送", 2), ("收件人", 2),
                ("每周", 2), ("每月", 2), ("每天", 2), ("定期", 2), ("流程", 2), ("待办", 2),
                ("任务", 2), ("日程", 2), ("提醒", 2),
                # 弱匹配
                ("办公", 1), ("习惯", 1), ("工作流", 1), ("日历", 1), ("几点", 1), ("之前", 1),
                ("之后", 1), ("固定", 1), ("惯例", 1), ("提交", 1), ("上线", 1), ("发布", 1)
            ],
            "feedback": [
                # 强匹配
                ("反馈", 2), ("建议", 2), ("修正", 2), ("不对", 2), ("错了", 2), ("纠正", 2),
                ("不要", 2), ("别", 2), ("禁止", 2), ("不要说", 2), ("必须", 2), ("应该", 2),
                ("需要", 2), ("下次", 2), ("注意", 2),
                # 弱匹配
                ("最好", 1), ("应该要", 1), ("应该是", 1), ("问题", 1), ("改", 1), ("调整", 1),
                ("改进", 1), ("回答", 1), ("回复", 1), ("希望", 1), ("要求", 1)
            ],
            "reference": [
                # 强匹配
                ("地址", 2), ("链接", 2), ("文档", 2), ("规范", 2), ("参考", 2), ("资料", 2),
                ("仓库", 2), ("git", 2), ("密码", 2), ("配置", 2), ("账号", 2), ("服务器", 2),
                ("接口", 2), ("文档地址", 2), ("下载地址", 2),
                # 弱匹配
                ("说明", 1), ("手册", 1), ("指南", 1), ("教程", 1), ("代码", 1), ("命令", 1),
                ("ip", 1), ("端口", 1), ("密钥", 1), ("token", 1), ("api", 1)
            ]
        }
        
        # 计算每个分类的匹配得分
        scores = {}
        total_possible_score = 0
        for category, keywords in category_keywords.items():
            score = 0
            for kw, weight in keywords:
                if kw in content_lower:
                    score += weight
            scores[category] = score
            total_possible_score += sum(w for _, w in keywords)
        
        # 找到得分最高的分类
        max_score = max(scores.values())
        sorted_scores = sorted(scores.values(), reverse=True)
        
        # 计算置信度：最高得分和第二高得分的差距越大，置信度越高
        confidence = 0.0
        if max_score > 0:
            second_score = sorted_scores[1] if len(sorted_scores) > 1 else 0
            score_gap = max_score - second_score
            confidence = min(max_score / 5.0 + score_gap / 3.0, 1.0)
        
        # 返回最高得分的分类
        for category, score in scores.items():
            if score == max_score:
                return category, confidence
        
        return "reference", 0.0
    
    def _llm_classify(self, content: str) -> str:
        """
        LLM语义分类，返回分类结果，调用失败返回None
        """
        try:
            from openai import OpenAI
            from cognix.utils.config import config
            
            # 复用现有LLM配置
            client = OpenAI(
                base_url=config.llm_base_url,
                api_key=config.llm_api_key
            )
            
            prompt = f"""
            请将以下内容分类到5个类别中，只返回类别名称，不要输出任何其他内容。
            可选类别：
            - user: 用户身份、个人信息、称呼、语言偏好、输出风格等
            - settings: 系统设置、偏好配置、输出格式、视图设置、通知规则等
            - office: 办公相关、会议、周报、流程、审批、联系人群组、周期性任务等
            - feedback: 用户反馈、纠正意见、使用要求、禁止操作、改进建议等
            - reference: 参考资料、链接地址、文档、配置信息、密码、通用知识等
            
            内容：{content}
            """
            
            response = client.chat.completions.create(
                model=config.llm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=10
            )
            
            result = response.choices[0].message.content.strip().lower()
            # 校验返回结果是否合法
            valid_categories = ["user", "settings", "office", "feedback", "reference"]
            if result in valid_categories:
                return result
            
            return None
        except Exception as e:
            # LLM调用失败时返回None，自动回退到规则分类
            return None
    
    def add_persistent_memory(self, heading: str, content: str):
        """
        添加持久记忆（兼容旧接口）
        自动分类到合适的分类存储，支持LLM语义分类增强
        """
        full_content = f"{heading} {content}"
        content_lower = full_content.lower()
        
        # 1. 先执行规则分类
        category, confidence = self._rule_classify(content_lower)
        
        # 2. 如果开启了LLM分类且规则置信度低于阈值，调用LLM二次分类
        from cognix.utils.config import config
        if config.llm_classification_enabled and confidence < config.llm_classification_confidence_threshold:
            llm_category = self._llm_classify(full_content)
            if llm_category:
                category = llm_category
        
        self.add_classified_memory(category, heading, content)
    
    def search_memory(self, query: str, limit: int = 10, source: Optional[str] = None) -> List[Dict]:
        """搜索记忆 - 优先使用FTS5全文搜索"""
        
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
        entries = self.short_term_memory.get(session_id, [])
        
        # 上下文裁剪逻辑
        from cognix.utils.config import config
        if config.context_trim_enabled and len(entries) > config.max_history_rounds * 2:
            # 每个轮次包含用户输入和AI输出两条，所以乘以2
            # 只保留最新的N轮
            start_idx = max(0, len(entries) - config.max_history_rounds * 2)
            return entries[start_idx:]
        
        return entries
    
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
        # 重建索引时清空所有缓存，重新提取
        cursor.execute('DELETE FROM cached_preferences')
        cursor.execute('DELETE FROM cached_entities')
        cursor.execute('DELETE FROM cached_habits')
        self._conn.commit()
        self._index_all_memory_files()
    
    # ===================== 结构化缓存操作方法 =====================
    def cache_preference(self, key: str, value: str, source_path: str, confidence: float = 1.0):
        """缓存用户偏好"""
        import time
        cursor = self._conn.cursor()
        now = int(time.time() * 1000)
        cursor.execute('''
            INSERT OR REPLACE INTO cached_preferences 
            (key, value, source_path, confidence, updated_at, extracted_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (key, value, source_path, confidence, now, now))
        self._conn.commit()
    
    def get_cached_preferences(self, key_prefix: str = "") -> List[Dict]:
        """获取缓存的偏好，支持前缀匹配"""
        cursor = self._conn.cursor()
        if key_prefix:
            cursor.execute('SELECT * FROM cached_preferences WHERE key LIKE ?', (f"{key_prefix}%",))
        else:
            cursor.execute('SELECT * FROM cached_preferences')
        
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def cache_entity(self, name: str, entity_type: str, content: str, source_path: str, 
                    summary: str = None, confidence: float = 0.8):
        """缓存实体"""
        import time
        import uuid
        cursor = self._conn.cursor()
        now = int(time.time() * 1000)
        entity_id = str(uuid.uuid4())
        
        cursor.execute('''
            INSERT OR REPLACE INTO cached_entities 
            (id, name, type, content, summary, source_path, confidence, updated_at, extracted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (entity_id, name, entity_type, content, summary, source_path, confidence, now, now))
        self._conn.commit()
        return entity_id
    
    def get_cached_entities(self, entity_type: str = None, name: str = None) -> List[Dict]:
        """获取缓存的实体，支持类型和名称过滤"""
        cursor = self._conn.cursor()
        params = []
        sql = 'SELECT * FROM cached_entities WHERE 1=1'
        
        if entity_type:
            sql += ' AND type = ?'
            params.append(entity_type)
        if name:
            sql += ' AND name LIKE ?'
            params.append(f"%{name}%")
        
        cursor.execute(sql, params)
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def cache_habit(self, pattern: str, habit_type: str, description: str, 
                   frequency: int = 1, confidence: float = 0.7):
        """缓存用户习惯"""
        import time
        import uuid
        cursor = self._conn.cursor()
        now = int(time.time() * 1000)
        habit_id = str(uuid.uuid4())
        
        cursor.execute('''
            INSERT OR REPLACE INTO cached_habits 
            (id, pattern, type, description, frequency, confidence, last_occurrence_at, extracted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (habit_id, pattern, habit_type, description, frequency, confidence, now, now))
        self._conn.commit()
        return habit_id
    
    def get_cached_habits(self, habit_type: str = None, min_confidence: float = 0.7) -> List[Dict]:
        """获取缓存的习惯，支持类型和最小置信度过滤"""
        cursor = self._conn.cursor()
        params = [min_confidence]
        sql = 'SELECT * FROM cached_habits WHERE confidence >= ?'
        
        if habit_type:
            sql += ' AND type = ?'
            params.append(habit_type)
        
        cursor.execute(sql, params)
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def invalidate_cache_by_path(self, source_path: str):
        """根据文件路径失效对应的缓存，文件更新时调用"""
        cursor = self._conn.cursor()
        cursor.execute('DELETE FROM cached_preferences WHERE source_path = ?', (source_path,))
        cursor.execute('DELETE FROM cached_entities WHERE source_path = ?', (source_path,))
        # 删除相关的实体和关系
        cursor.execute('DELETE FROM entities WHERE source_path = ?', (source_path,))
        cursor.execute('DELETE FROM entity_relations WHERE source_path = ?', (source_path,))
        # 习惯是全局的，不关联单个文件，不需要失效
        self._conn.commit()
    
    # ===================== 实体关系操作方法 =====================
    def add_entity(self, name: str, entity_type: str, content: str, source_path: str,
                  summary: str = None, confidence: float = 0.8) -> str:
        """添加实体"""
        import time
        import uuid
        cursor = self._conn.cursor()
        now = int(time.time() * 1000)
        entity_id = str(uuid.uuid4())
        
        cursor.execute('''
            INSERT OR REPLACE INTO entities 
            (id, name, type, content, summary, source_path, confidence, updated_at, extracted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (entity_id, name, entity_type, content, summary, source_path, confidence, now, now))
        self._conn.commit()
        return entity_id
    
    def get_entity(self, entity_id: str = None, name: str = None, entity_type: str = None) -> List[Dict]:
        """查询实体，支持按ID、名称、类型过滤"""
        cursor = self._conn.cursor()
        params = []
        sql = 'SELECT * FROM entities WHERE 1=1'
        
        if entity_id:
            sql += ' AND id = ?'
            params.append(entity_id)
        if name:
            sql += ' AND name LIKE ?'
            params.append(f"%{name}%")
        if entity_type:
            sql += ' AND type = ?'
            params.append(entity_type)
        
        cursor.execute(sql, params)
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def add_relation(self, from_entity_id: str, to_entity_id: str, relation_type: str, 
                    source_path: str, confidence: float = 0.7) -> str:
        """添加实体间关系"""
        import time
        import uuid
        cursor = self._conn.cursor()
        now = int(time.time() * 1000)
        relation_id = str(uuid.uuid4())
        
        # 避免重复关系
        cursor.execute('''
            SELECT id FROM entity_relations 
            WHERE from_entity_id = ? AND to_entity_id = ? AND relation_type = ?
        ''', (from_entity_id, to_entity_id, relation_type))
        existing = cursor.fetchone()
        if existing:
            return existing[0]
        
        cursor.execute('''
            INSERT INTO entity_relations 
            (id, from_entity_id, to_entity_id, relation_type, confidence, source_path, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (relation_id, from_entity_id, to_entity_id, relation_type, confidence, source_path, now))
        self._conn.commit()
        return relation_id
    
    def get_entity_relations(self, entity_id: str, relation_type: str = None, direction: str = "both") -> List[Dict]:
        """
        获取实体的关联关系
        :param entity_id: 实体ID
        :param relation_type: 关系类型过滤，可选
        :param direction: 关联方向：from/to/both
        :return: 关联关系列表
        """
        cursor = self._conn.cursor()
        params = []
        sql_parts = []
        
        if direction in ["from", "both"]:
            sql_parts.append('SELECT * FROM entity_relations WHERE from_entity_id = ?')
            params.append(entity_id)
        if direction in ["to", "both"]:
            if sql_parts:
                sql_parts.append('UNION ALL')
            sql_parts.append('SELECT * FROM entity_relations WHERE to_entity_id = ?')
            params.append(entity_id)
        
        if not sql_parts:
            return []
        
        sql = ' '.join(sql_parts)
        if relation_type:
            sql += ' AND relation_type = ?'
            params.append(relation_type)
        
        cursor.execute(sql, params)
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def get_related_entities(self, entity_id: str, max_depth: int = 3) -> List[Dict]:
        """
        递归获取关联实体，支持多跳查询（默认3跳）
        :param entity_id: 起始实体ID
        :param max_depth: 最大跳数
        :return: 关联实体列表，包含深度信息
        """
        cursor = self._conn.cursor()
        # 先检查实体是否存在
        cursor.execute("SELECT 1 FROM entities WHERE id = ?", (entity_id,))
        if not cursor.fetchone():
            return []
        
        try:
            # 使用SQLite递归CTE实现多跳查询，避免循环引用
            cursor.execute('''
                WITH RECURSIVE entity_hierarchy AS (
                    SELECT id, name, type, summary, 0 as depth, CAST(',' || id || ',' AS TEXT) as visited
                    FROM entities WHERE id = ?
                    UNION ALL
                    SELECT e.id, e.name, e.type, e.summary, eh.depth + 1 as depth, 
                           eh.visited || e.id || ',' as visited
                    FROM entity_hierarchy eh
                    JOIN entity_relations r ON 
                        r.from_entity_id = eh.id OR r.to_entity_id = eh.id
                    JOIN entities e ON
                        (e.id = r.to_entity_id AND e.id != eh.id)
                        OR (e.id = r.from_entity_id AND e.id != eh.id)
                    WHERE eh.depth < ? AND eh.visited NOT LIKE '%,' || e.id || ',%'
                )
                SELECT DISTINCT id, name, type, summary, depth FROM entity_hierarchy WHERE depth > 0 ORDER BY depth
            ''', (entity_id, max_depth))
            
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except Exception as e:
            # 递归查询出错时返回空，避免影响主流程
            import logging
            logging.getLogger(__name__).warning(f"多跳查询失败: {str(e)}")
            return []
    
    def get_pending_compression_sessions(self) -> List[Dict]:
        """
        获取所有待压缩的会话
        :return: 会话列表，包含id和content
        """
        sessions = []
        for session_id, entries in self.short_term_memory.items():
            # 组装会话内容
            content_parts = []
            for entry in entries:
                content_parts.append(f"{entry.get('key', '')}: {entry.get('value', '')}")
            
            content = "\n".join(content_parts)
            if content.strip():
                sessions.append({
                    "id": session_id,
                    "content": content
                })
        
        return sessions
    
    def mark_session_compressed(self, session_id: str):
        """
        标记会话已压缩，清除短期记忆
        :param session_id: 会话ID
        """
        self.clear_short_term(session_id)
    
    def archive_old_sessions(self, before_date: datetime) -> int:
        """
        归档指定日期之前的会话
        :param before_date: 归档截止日期
        :return: 归档的会话数量
        """
        # 目前短期记忆是内存存储，暂无历史会话，返回0
        # 后续接入Redis后完善该功能
        return 0
    
    def cleanup_archived_sessions(self, before_date: datetime) -> int:
        """
        清理指定日期之前的已归档会话
        :param before_date: 清理截止日期
        :return: 清理的会话数量
        """
        # 后续完善该功能
        return 0
    
    def mount_external_content(self, content: str, source_name: str, 
                              auto_classify: bool = True) -> str:
        """
        挂载外部内容，自动加入记忆系统（对应memU的Mount points功能）
        :param content: 外部内容，可以是文本、Markdown、JSON等
        :param source_name: 内容来源名称，用于识别来源
        :param auto_classify: 是否自动分类，默认True
        :return: 生成的记忆ID
        """
        import uuid
        import time
        memory_id = str(uuid.uuid4())
        now = int(time.time() * 1000)
        
        if auto_classify:
            # 自动分类到合适的分类
            self.add_persistent_memory(f"外部导入-{source_name}", content)
        else:
            # 默认添加到reference分类
            self.add_classified_memory("reference", f"外部导入-{source_name}", content)
        
        # 自动触发实体抽取和关联建链
        # 后续会在Autodream中自动处理新导入的内容
        
        return memory_id
    
    def mount_file(self, file_path: str, auto_classify: bool = True) -> str:
        """
        挂载外部文件，支持.md/.txt/.json格式
        :param file_path: 文件路径
        :param auto_classify: 是否自动分类
        :return: 记忆ID
        """
        from pathlib import Path
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在：{file_path}")
        
        content = path.read_text(encoding='utf-8')
        return self.mount_external_content(content, path.name, auto_classify)
    
    def export_memory(self, export_path: str = None, include_sessions: bool = True) -> str:
        """
        导出所有记忆为纯Markdown压缩包
        :param export_path: 导出路径，默认导出到当前目录
        :param include_sessions: 是否包含历史会话
        :return: 导出文件路径
        """
        import zipfile
        from pathlib import Path
        import time
        
        if not export_path:
            export_path = f"cognix_memory_export_{int(time.time())}.zip"
        
        with zipfile.ZipFile(export_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # 导出分类记忆
            for category in ["user", "settings", "office", "feedback", "reference"]:
                file_path = self.classifier.get_category_path(category)
                if file_path.exists():
                    zf.write(file_path, f"memory/{category}.md")
            
            # 导出每日日志
            for md_file in self.memory_dir.glob("*.md"):
                if md_file.stem not in ["user", "settings", "office", "feedback", "reference"]:
                    zf.write(md_file, f"memory/{md_file.name}")
            
            # 导出生成的技能
            skills_dir = self.memory_dir / "skills"
            if skills_dir.exists():
                for skill_file in skills_dir.glob("*.py"):
                    zf.write(skill_file, f"skills/{skill_file.name}")
            
            # 导出历史会话
            if include_sessions and self.sessions_dir.exists():
                for session_file in self.sessions_dir.glob("*.md"):
                    zf.write(session_file, f"sessions/{session_file.name}")
        
        return str(Path(export_path).absolute())
    
    def import_memory(self, import_zip_path: str, overwrite: bool = False) -> int:
        """
        从导出的压缩包导入记忆
        :param import_zip_path: 压缩包路径
        :param overwrite: 是否覆盖现有文件，默认不覆盖
        :return: 导入的文件数量
        """
        import zipfile
        from pathlib import Path
        
        path = Path(import_zip_path)
        if not path.exists():
            raise FileNotFoundError(f"导入文件不存在：{import_zip_path}")
        
        imported_count = 0
        
        with zipfile.ZipFile(import_zip_path, 'r') as zf:
            for file_info in zf.infolist():
                if file_info.is_dir():
                    continue
                
                # 跳过系统文件
                if file_info.filename.startswith('__MACOSX') or file_info.filename.endswith('.DS_Store'):
                    continue
                
                # 确定目标路径
                if file_info.filename.startswith('memory/'):
                    target_path = self.memory_dir / file_info.filename[7:]
                elif file_info.filename.startswith('skills/'):
                    target_path = self.memory_dir / "skills" / file_info.filename[7:]
                elif file_info.filename.startswith('sessions/'):
                    target_path = self.sessions_dir / file_info.filename[9:]
                else:
                    # 未知路径，跳过
                    continue
                
                if target_path.exists() and not overwrite:
                    # 不覆盖现有文件，跳过
                    continue
                
                # 创建父目录
                target_path.parent.mkdir(parents=True, exist_ok=True)
                
                # 写入文件
                with zf.open(file_info) as source, open(target_path, 'wb') as target:
                    target.write(source.read())
                
                # 索引新导入的文件
                if target_path.suffix == '.md':
                    self._index_markdown_file(target_path)
                
                imported_count += 1
        
        # 导入完成后重建索引
        self.rebuild_index()
        
        return imported_count
    
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
