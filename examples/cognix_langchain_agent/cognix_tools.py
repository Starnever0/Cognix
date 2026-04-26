"""
Cognix 记忆系统工具封装（非侵入式CLI调用）
完全通过子进程调用Cognix CLI命令，不依赖Cognix内部代码
"""
import subprocess
import json
import shlex
from typing import List, Dict, Optional, Any

class CognixMemoryTool:
    def __init__(self, cognix_cmd: str = "python -m cognix"):
        """
        初始化Cognix工具
        :param cognix_cmd: Cognix CLI命令，默认使用模块调用
        """
        self.cognix_cmd = cognix_cmd
    
    def _run_command(self, args: List[str]) -> Dict[str, Any]:
        """运行CLI命令并返回结果"""
        try:
            cmd = f"{self.cognix_cmd} {' '.join(shlex.quote(arg) for arg in args)}"
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                encoding="utf-8"
            )
            
            if result.returncode != 0:
                return {
                    "success": False,
                    "error": result.stderr,
                    "returncode": result.returncode
                }
            
            # 尝试解析JSON输出
            try:
                return {
                    "success": True,
                    "data": json.loads(result.stdout.strip())
                }
            except json.JSONDecodeError:
                # 非JSON输出（比如context命令返回纯文本）
                return {
                    "success": True,
                    "data": result.stdout.strip()
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def remember(self, heading: str, content: str, persistent: bool = False) -> Dict[str, Any]:
        """
        记录记忆
        :param heading: 记忆标题
        :param content: 记忆内容
        :param persistent: 是否保存为持久记忆
        :return: 执行结果
        """
        args = ["remember", heading, content]
        if persistent:
            args.append("--persistent")
        return self._run_command(args)
    
    def recall(self, query: str, limit: int = 5, source: Optional[str] = None) -> Dict[str, Any]:
        """
        搜索记忆
        :param query: 搜索关键词
        :param limit: 返回结果数量
        :param source: 来源过滤（memory/persistent）
        :return: 搜索结果
        """
        args = ["recall", query, "--limit", str(limit)]
        if source:
            args.extend(["--source", source])
        return self._run_command(args)
    
    def get_context(self, days: int = 1) -> Dict[str, Any]:
        """
        获取近期上下文
        :param days: 回溯天数
        :return: 上下文文本
        """
        args = ["context", "--days", str(days)]
        return self._run_command(args)
    
    def dream(self) -> Dict[str, Any]:
        """手动触发记忆整理"""
        return self._run_command(["dream"])

# 工具描述（用于LLM工具调用）
COGNIX_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "remember",
            "description": "记录重要信息到记忆系统，包括用户偏好、重要决策、关键事实、工作习惯等",
            "parameters": {
                "type": "object",
                "properties": {
                    "heading": {
                        "type": "string",
                        "description": "记忆的标题，简短概括内容，例如'用户偏好'、'项目决策'、'工作习惯'"
                    },
                    "content": {
                        "type": "string",
                        "description": "记忆的详细内容"
                    },
                    "persistent": {
                        "type": "boolean",
                        "description": "是否保存为持久记忆（永久保留，跨会话可用），默认False"
                    }
                },
                "required": ["heading", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "recall",
            "description": "搜索与当前问题相关的历史记忆，用于回答需要上下文的问题",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词，与要查找的内容相关"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回结果数量，默认5"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_context",
            "description": "获取最近几天的所有对话和记忆上下文，用于了解近期发生的事情",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "description": "回溯天数，默认1"
                    }
                }
            }
        }
    }
]
