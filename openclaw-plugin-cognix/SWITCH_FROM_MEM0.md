# 从 Mem0 切换到 Cognix 极简指南

## 切换步骤（仅需 2 步，5 分钟完成）

### 1. 安装 Cognix 插件
```bash
openclaw plugins install @starnever0/openclaw-cognix-plugin
```

### 2. 修改配置切换记忆插件
编辑 OpenClaw 配置文件（通常为 `~/.openclaw/config.yaml` 或工作区 `.openclaw/config.yaml`），找到以下配置项：
```yaml
plugins:
  slots:
    memory: "openclaw-mem0-plugin"  # 将这行修改为下方值
```
修改为：
```yaml
plugins:
  slots:
    memory: "openclaw-cognix-plugin"
```

### 3. 重启 OpenClaw 即可生效
```bash
openclaw restart
```

## 兼容性说明
✅ 完全兼容 Mem0 所有接口，现有业务代码无需任何修改  
✅ 原有记忆数据可自动迁移（首次启动时自动执行）  
✅ 原有的 `autoRecall`、`autoCapture` 配置保持不变  
✅ 支持所有现有记忆相关工具调用（`memory_search`/`memory_write`等）

## 回滚方案
如果需要切回 Mem0，只需将 `plugins.slots.memory` 改回 `openclaw-mem0-plugin` 并重启即可。
