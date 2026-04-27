from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from cognix.core.preference_store import preference_store
from cognix.storage.event_store import file_store
from cognix.core.memory_system import MarkdownMemory
import uuid
import json
import re

# 初始化记忆系统
memory_system = MarkdownMemory()

app = FastAPI(title="Cognix Memory API", version="1.0")

# ========== Mem0 兼容请求响应模型 ==========
class Mem0MemoryStoreRequest(BaseModel):
    messages: Optional[List[Dict[str, str]]] = None
    content: Optional[str] = None
    text: Optional[str] = None  # 兼容多种参数名
    long_term: bool = Field(True, alias="longTerm")  # 默认存储为长期记忆
    user_id: str = Field("default", alias="userId")
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        populate_by_name = True
        extra = "allow"

class Mem0MemorySearchRequest(BaseModel):
    query: str
    user_id: str = Field("default", alias="userId")
    limit: int = 10
    filters: Optional[Dict[str, Any]] = None
    
    class Config:
        populate_by_name = True
        extra = "allow"

class Mem0MemoryItem(BaseModel):
    id: str
    memory: str
    content: Optional[str] = None
    user_id: str
    created_at: str
    updated_at: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    score: Optional[float] = 1.0

# ========== 工具函数 ==========
def _match_preference(text: str) -> Optional[str]:
    """尝试匹配文本中的偏好设置"""
    patterns = [
        r"(我)?喜欢|偏好|习惯|以后|总是|每次.*(用|要|是|发给|格式为|为)[\"\"'](?P<value>[^\"\"']+)[\"\"']",
        r"(报告|周报|会议).*格式.*(?P<value>markdown|table|md|表格)",
        r"(周报|邮件).*发给.*(?P<value>[a-zA-Z0-9\u4e00-\u9fa5,，]+)",
        r"提前(?P<value>\d+)分钟提醒",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group("value")
    return None

def _get_content(req: Mem0MemoryStoreRequest) -> str:
    """兼容mem0多种传参方式"""
    if req.messages:
        # 如果是消息数组，拼接成字符串
        return "\n".join([f"{m.get('role', '')}: {m.get('content', '')}" for m in req.messages])
    elif req.content:
        return req.content
    elif req.text:
        return req.text
    return ""

# ========== Mem0 兼容API接口 ==========
@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "ok", "service": "cognix-memory", "timestamp": datetime.now().isoformat()}

@app.get("/v1/ping/")
async def mem0_ping_check():
    """Mem0兼容健康检查接口"""
    return {"status": "ok", "service": "cognix-memory", "timestamp": datetime.now().isoformat()}

# ========== Mem0 标准接口：完全兼容路径和格式 ==========
@app.post("/v1/memories/", response_model=Mem0MemoryItem)
async def mem0_store_memory(req: Mem0MemoryStoreRequest):
    """存储记忆：兼容Mem0 POST /v1/memories/ 接口"""
    memory_id = str(uuid.uuid4())
    content = _get_content(req)
    now = datetime.now().isoformat()
    
    event_data = {
        "content": content,
        "long_term": req.long_term,
        "metadata": req.metadata or {}
    }
    
    # 存储到事件系统
    file_store.add_event("memory_stored", event_data)
    
    # 存储到Markdown记忆系统
    if req.long_term:
        # 自动分类标题
        heading = "事实记忆"
        if "偏好" in content or "喜欢" in content or "习惯" in content:
            heading = "用户偏好"
        elif "项目" in content or "开发" in content or "任务" in content:
            heading = "项目笔记"
        elif "会议" in content or "周报" in content or "流程" in content:
            heading = "办公相关"
            
        memory_system.add_memory(heading, content)
    
    # 尝试自动识别偏好设置，自动存入偏好系统
    pref_value = _match_preference(content)
    if pref_value and req.long_term:
        # 简单的偏好识别，后续可以扩展更智能的识别逻辑
        if "格式" in content and ("markdown" in pref_value.lower() or "table" in pref_value.lower() or "md" in pref_value.lower()):
            try:
                fmt = "markdown" if "md" in pref_value.lower() or "markdown" in pref_value.lower() else "table"
                preference_store.set("report_format", fmt)
            except:
                pass
        elif "周报" in content and "发给" in content:
            try:
                preference_store.set("weekly_report_receiver", pref_value.strip())
            except:
                pass
        elif "分钟提醒" in content:
            try:
                minutes = int(pref_value)
                preference_store.set("meeting_reminder_before", minutes)
            except:
                pass
    
    return Mem0MemoryItem(
        id=memory_id,
        memory=content,
        content=content,
        user_id=req.user_id,
        created_at=now,
        updated_at=now,
        metadata=req.metadata,
        score=1.0
    )

@app.post("/v1/memories/search/", response_model=List[Mem0MemoryItem])
async def mem0_search_memory(req: Mem0MemorySearchRequest):
    """搜索记忆：兼容Mem0 POST /v1/memories/search/ 接口"""
    memories = []
    now = datetime.now().isoformat()
    
    # 1. 优先搜索用户偏好，优先级最高，score 1.0
    prefs = preference_store.list()
    for pref in prefs:
        # 简单关键词匹配
        if req.query.lower() in pref["description"].lower() or req.query.lower() in str(pref["value"]).lower():
            memories.append(Mem0MemoryItem(
                id=f"pref_{pref['key']}",
                memory=f"{pref['description']}: {pref['value']}",
                content=f"{pref['description']}: {pref['value']}",
                user_id=req.user_id,
                created_at=pref["updated_at"] or now,
                updated_at=pref["updated_at"] or now,
                metadata={"weight": pref["weight"], "type": "preference"},
                score=1.0  # 偏好权重最高
            ))
    
    # 2. 搜索Markdown记忆库，score 0.9
    markdown_results = memory_system.search_memory(req.query, limit=req.limit)
    for result in markdown_results:
        memories.append(Mem0MemoryItem(
            id=result["id"],
            memory=result["text"],
            content=result["text"],
            user_id=req.user_id,
            created_at=now,
            updated_at=now,
            metadata={"source": result["source"], "path": result["path"], "type": "markdown"},
            score=0.9
        ))
    
    # 3. 搜索历史记忆事件，score 0.8
    events = file_store.get_events(limit=req.limit * 2)  # 多取一些后过滤
    for event in events:
        event_content = json.dumps(event["data"], ensure_ascii=False)
        if req.query.lower() in event_content.lower():
            memories.append(Mem0MemoryItem(
                id=event["event_id"],
                memory=event_content,
                content=event_content,
                user_id=req.user_id,
                created_at=event["timestamp"],
                updated_at=event["timestamp"],
                metadata={"event_type": event["type"], "type": "event"},
                score=0.8
            ))
    
    # 按score降序排序，限制返回数量
    memories.sort(key=lambda x: x.score, reverse=True)
    return memories[:req.limit]

@app.get("/v1/memories/{memory_id}/", response_model=Mem0MemoryItem)
async def mem0_get_memory(memory_id: str):
    """获取记忆：兼容Mem0 GET /v1/memories/{id}/ 接口"""
    # 先查事件
    event = file_store.get_event_by_id(memory_id)
    if event:
        event_content = json.dumps(event["data"], ensure_ascii=False)
        return Mem0MemoryItem(
            id=memory_id,
            memory=event_content,
            content=event_content,
            user_id="default",
            created_at=event["timestamp"],
            updated_at=event["timestamp"],
            metadata={"event_type": event["type"]},
            score=0.8
        )
    
    # 再查偏好（如果是偏好ID）
    if memory_id.startswith("pref_"):
        pref_key = memory_id[5:]
        pref_value = preference_store.get(pref_key)
        if pref_value is not None:
            pref_meta = preference_store.get_with_meta(pref_key)
            now = datetime.now().isoformat()
            return Mem0MemoryItem(
                id=memory_id,
                memory=f"{pref_meta['meta'].get('description', '')}: {pref_value}",
                content=f"{pref_meta['meta'].get('description', '')}: {pref_value}",
                user_id="default",
                created_at=pref_meta.get("created_at", now),
                updated_at=pref_meta.get("updated_at", now),
                metadata={"weight": pref_meta.get("weight", 1.0)},
                score=1.0
            )
    
    raise HTTPException(status_code=404, detail="Memory not found")

@app.get("/v1/memories/", response_model=Dict[str, Any])
async def mem0_list_memories(
    user_id: str = Query("default", alias="userId"),
    limit: int = Query(20),
    page: int = Query(1)
):
    """列出记忆：兼容Mem0 GET /v1/memories/?user_id=xxx 接口"""
    events = file_store.get_events(limit=limit)
    memories = []
    now = datetime.now().isoformat()
    
    for event in events:
        event_content = json.dumps(event["data"], ensure_ascii=False)
        memories.append(Mem0MemoryItem(
            id=event["event_id"],
            memory=event_content,
            content=event_content,
            user_id=user_id,
            created_at=event["timestamp"],
            updated_at=event["timestamp"],
            metadata={"event_type": event["type"]},
            score=0.8
        ))
    
    return {
        "results": memories,
        "count": len(memories),
        "page": page,
        "limit": limit,
        "total": len(memories)
    }

@app.delete("/v1/memories/{memory_id}/", response_model=Dict[str, Any])
async def mem0_delete_memory(memory_id: str):
    """删除记忆：兼容Mem0 DELETE /v1/memories/{id}/ 接口"""
    # 标记为删除（实际保留日志）
    file_store.add_event("memory_deleted", {"memory_id": memory_id})
    return {
        "status": "ok",
        "message": "Memory deleted successfully"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8765)
