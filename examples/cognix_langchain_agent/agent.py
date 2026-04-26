"""
极简Cognix记忆增强智能体
支持OpenAI/Anthropic等多种LLM，非侵入式接入Cognix记忆系统
"""
import os
import json
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from cognix_tools import CognixMemoryTool, COGNIX_TOOLS

# 自动检测可用的SDK
HAVE_OPENAI = False
HAVE_ANTHROPIC = False

try:
    from openai import OpenAI
    HAVE_OPENAI = True
except ImportError:
    pass

try:
    from anthropic import Anthropic
    HAVE_ANTHROPIC = True
except ImportError:
    pass

# 加载环境变量
load_dotenv()

class CognixAgent:
    def __init__(self, provider: Optional[str] = None, model: Optional[str] = None, base_url: Optional[str] = None):
        """
        初始化智能体
        :param provider: LLM供应商，支持 openai / anthropic，默认从环境变量读取LLM_PROVIDER
        :param model: LLM模型名称，默认从环境变量读取
        :param base_url: API地址，默认从环境变量读取
        """
        # 默认从环境变量读取配置
        self.provider = (provider or os.getenv("LLM_PROVIDER", "openai")).lower()
        self.cognix_tool = CognixMemoryTool()
        self.conversation_history: List[Dict[str, Any]] = []
        
        # 初始化客户端
        if self.provider == "openai":
            if not HAVE_OPENAI:
                raise ImportError("请先安装openai SDK: pip install openai")
                
            self.client = OpenAI(
                api_key=os.getenv("OPENAI_API_KEY"),
                base_url=base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
            )
            self.model = model or os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
            
        elif self.provider == "anthropic":
            if not HAVE_ANTHROPIC:
                raise ImportError("请先安装anthropic SDK: pip install anthropic")
                
            self.client = Anthropic(
                api_key=os.getenv("ANTHROPIC_API_KEY"),
                base_url=base_url or os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
            )
            self.model = model or os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet-20240229")
            
        else:
            raise ValueError(f"不支持的LLM供应商: {self.provider}，目前支持 openai / anthropic")
        
        # 系统提示词
        self.system_prompt = """
你是一个拥有长期记忆能力的AI助手，能够记住用户的偏好、习惯和历史对话信息。

核心规则：
1. 当用户提到重要信息（个人信息、偏好、习惯、决策等）时，立即调用remember工具将信息保存到记忆系统
2. 当回答用户问题时，如果需要历史信息才能回答，先调用recall工具搜索相关记忆
3. 当用户问起近期发生的事情时，调用get_context工具获取近期上下文
4. 不要告诉用户你在调用工具，自然地整合记忆信息到回答中
5. 回答要简洁、准确，符合用户的偏好

记忆系统会自动分类存储信息，你不需要关心存储细节，只需要调用工具即可。
"""
    
    def _call_llm(self, messages: List[Dict[str, Any]], tools: List[Any] = None) -> Any:
        """调用LLM API"""
        if self.provider == "openai":
            return self._call_openai(messages, tools)
        elif self.provider == "anthropic":
            return self._call_anthropic(messages, tools)
    
    def _call_openai(self, messages: List[Dict[str, Any]], tools: List[Any] = None) -> Any:
        """调用OpenAI格式API"""
        params = {
            "model": self.model,
            "messages": [{"role": "system", "content": self.system_prompt}] + messages,
            "temperature": 0.7
        }
        if tools:
            params["tools"] = tools
            params["tool_choice"] = "auto"
        
        response = self.client.chat.completions.create(**params)
        message = response.choices[0].message
        
        # 统一返回格式
        return type('Message', (), {
            'content': message.content,
            'tool_calls': message.tool_calls
        })()
    
    def _call_anthropic(self, messages: List[Dict[str, Any]], tools: List[Any] = None) -> Any:
        """调用Anthropic Claude API"""
        # 转换工具格式为Anthropic格式
        anthropic_tools = None
        if tools:
            anthropic_tools = []
            for tool in tools:
                if tool["type"] == "function":
                    anthropic_tools.append({
                        "name": tool["function"]["name"],
                        "description": tool["function"]["description"],
                        "input_schema": tool["function"]["parameters"]
                    })
        
        params = {
            "model": self.model,
            "system": self.system_prompt,
            "messages": messages,
            "max_tokens": 1024,
            "temperature": 0.7
        }
        if anthropic_tools:
            params["tools"] = anthropic_tools
        
        response = self.client.messages.create(**params)
        
        # 提取内容和工具调用
        content = ""
        tool_calls = []
        
        for block in response.content:
            if block.type == "text":
                content += block.text
            elif block.type == "tool_use":
                # 转换为OpenAI格式的tool_call
                tool_calls.append(type('ToolCall', (), {
                    'id': block.id,
                    'function': type('Function', (), {
                        'name': block.name,
                        'arguments': json.dumps(block.input, ensure_ascii=False)
                    })()
                })())
        
        # 统一返回格式
        return type('Message', (), {
            'content': content,
            'tool_calls': tool_calls if tool_calls else None
        })()
    
    def _execute_tool_call(self, tool_call: Any) -> Dict[str, Any]:
        """执行工具调用"""
        function_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)
        
        print(f"[工具调用] {function_name}: {arguments}")
        
        if function_name == "remember":
            result = self.cognix_tool.remember(
                heading=arguments["heading"],
                content=arguments["content"],
                persistent=arguments.get("persistent", False)
            )
        elif function_name == "recall":
            result = self.cognix_tool.recall(
                query=arguments["query"],
                limit=arguments.get("limit", 5)
            )
        elif function_name == "get_context":
            result = self.cognix_tool.get_context(
                days=arguments.get("days", 1)
            )
        else:
            result = {"success": False, "error": f"未知工具: {function_name}"}
        
        # 适配不同供应商的tool返回格式
        if self.provider == "openai":
            return {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": function_name,
                "content": json.dumps(result, ensure_ascii=False)
            }
        elif self.provider == "anthropic":
            return {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_call.id,
                        "content": json.dumps(result, ensure_ascii=False)
                    }
                ]
            }
    
    def chat(self, user_input: str) -> str:
        """
        和智能体对话
        :param user_input: 用户输入
        :return: 智能体回答
        """
        # 添加用户输入到对话历史
        self.conversation_history.append({"role": "user", "content": user_input})
        
        # 第一轮调用，检查是否需要工具
        response = self._call_llm(self.conversation_history, COGNIX_TOOLS)
        
        # 处理工具调用
        while response.tool_calls:
            tool_messages = []
            for tool_call in response.tool_calls:
                tool_result = self._execute_tool_call(tool_call)
                tool_messages.append(tool_result)
            
            # 添加工具结果到消息
            if self.provider == "openai":
                self.conversation_history.append({
                    "role": "assistant",
                    "content": response.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        } for tc in response.tool_calls
                    ]
                })
            elif self.provider == "anthropic":
                # 构建Anthropic格式的assistant消息
                content_blocks = []
                if response.content:
                    content_blocks.append({
                        "type": "text",
                        "text": response.content
                    })
                for tc in response.tool_calls:
                    content_blocks.append({
                        "type": "tool_use",
                        "id": tc.id,
                        "name": tc.function.name,
                        "input": json.loads(tc.function.arguments)
                    })
                self.conversation_history.append({
                    "role": "assistant",
                    "content": content_blocks
                })
            
            self.conversation_history.extend(tool_messages)
            
            # 再次调用LLM生成回答
            response = self._call_llm(self.conversation_history, COGNIX_TOOLS)
        
        # 添加回答到对话历史
        self.conversation_history.append({"role": "assistant", "content": response.content})
        
        return response.content
    
    def clear_history(self):
        """清除对话历史"""
        self.conversation_history = []
