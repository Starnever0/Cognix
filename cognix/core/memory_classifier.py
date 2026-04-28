from pathlib import Path
from typing import List, Dict, Optional

class MemoryClassifier:
    """
    长期记忆分类管理器
    将记忆分为5个分类文件存储，并管理sessions和skills目录
    """
    CATEGORIES = ["user", "settings", "office", "feedback", "reference"]
    
    def __init__(self, memory_dir: str):
        self.memory_dir = Path(memory_dir)
        self._init_structure()
    
    def _init_structure(self):
        """初始化目录结构和分类文件"""
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建分类文件
        for category in self.CATEGORIES:
            file_path = self.memory_dir / f"{category}.md"
            if not file_path.exists():
                file_path.write_text(f"# {category.capitalize()} 记忆\n\n", encoding="utf-8")
        
        # 创建目录
        (self.memory_dir / "sessions").mkdir(exist_ok=True)
        (self.memory_dir / "skills").mkdir(exist_ok=True)
    
    def add_memory(self, category: str, heading: str, content: str) -> None:
        """
        添加分类记忆
        :param category: 分类名称，必须是CATEGORIES中的一个
        :param heading: 记忆标题（## 后面的内容）
        :param content: 记忆内容
        """
        if category not in self.CATEGORIES:
            raise ValueError(f"Invalid category: {category}, must be one of {self.CATEGORIES}")
        
        file_path = self.memory_dir / f"{category}.md"
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(f"\n## {heading}\n\n{content}\n")
    
    def get_memory(self, category: str) -> str:
        """
        获取分类记忆的全部内容
        :param category: 分类名称
        :return: 分类文件的完整内容
        """
        if category not in self.CATEGORIES:
            raise ValueError(f"Invalid category: {category}, must be one of {self.CATEGORIES}")
        
        file_path = self.memory_dir / f"{category}.md"
        return file_path.read_text(encoding="utf-8")
    
    def list_categories(self) -> List[str]:
        """获取所有可用分类列表"""
        return self.CATEGORIES.copy()
    
    def get_category_path(self, category: str) -> Path:
        """获取分类文件的路径"""
        if category not in self.CATEGORIES:
            raise ValueError(f"Invalid category: {category}, must be one of {self.CATEGORIES}")
        return self.memory_dir / f"{category}.md"
