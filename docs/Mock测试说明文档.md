# Mock Agent 记忆系统测试说明

## 概述

本文档说明如何使用 `mock_agent_memory_test.py` 脚本进行记忆系统的模拟测试，该脚本模拟了真实的Agent与记忆系统的完整交互场景。

## 测试文件位置

`tests/mock_agent_memory_test.py`

## 测试场景

该Mock测试包含以下8个完整场景：

### 场景1: 初始化用户信息
- 添加用户基本信息（姓名、年龄、角色）
- 添加工作信息（公司、部门、职位）
- 添加联系方式
- 验证记忆存储成功

### 场景2: 记录用户偏好
- 主题偏好（深色主题）
- 语言偏好（中文）
- 响应风格（简洁）
- 编程语言偏好（Python）

### 场景3: 记录用户交互
- 添加短期记忆（会话级别）
- 记录当前任务状态
- 记录Agent交互历史

### 场景4: 关联相关记忆
- 添加项目信息
- 建立记忆之间的关联（related_to、derived_from）
- 查询关联记忆

### 场景5: 为Agent准备上下文
- 整合短期记忆和长期记忆
- 按类型分类整理（事实、偏好、经验）
- 生成Agent可用的上下文

### 场景6: 搜索相关记忆
- 关键词搜索
- 按记忆类型搜索
- 混合条件搜索

### 场景7: 遗忘某些记忆
- 添加临时记忆
- 删除指定记忆
- 验证删除结果

### 场景8: 上下文总结
- 统计长期记忆
- 查看Markdown文件存储
- 展示记忆系统状态

## 运行方式

### 方式1: 直接运行脚本（自动清理）

```bash
python tests/mock_agent_memory_test.py
```

### 方式2: 保留测试文件用于检查

```bash
python tests/mock_agent_memory_test.py --keep
```

### 方式3: 指定输出目录

```bash
python tests/mock_agent_memory_test.py --output-dir ./my_test_data
```

### 方式4: 查看帮助

```bash
python tests/mock_agent_memory_test.py --help
```

### 方式5: 使用pytest

```bash
pytest tests/mock_agent_memory_test.py -v
```

## 命令行参数说明

| 参数 | 说明 |
|------|------|
| `--keep` | 测试完成后保留测试文件，不立即清理，用于检查 Markdown 文件等 |
| `--output-dir DIR` | 指定输出目录，不使用临时目录 |
| `--help` | 显示帮助信息 |

## 输出说明

测试脚本会实时输出每个步骤的执行结果：

- [OK] 成功 - 表示操作成功
- [FAIL] 失败 - 表示操作失败
- 状态、消息、数据 - 显示详细的返回信息

## 测试数据说明

默认情况下，所有测试数据都会存储在临时目录中，测试结束后自动清理，不会污染生产环境。

使用 `--keep` 选项可以保留测试文件，用于检查生成的 Markdown 文件和 SQLite 数据库。

临时目录位置：`d:/Mycode/LLM/Cognix/tmp*`

## 清理测试文件

当使用 `--keep` 选项保留测试文件后，可以使用清理脚本进行清理：

### 方式1: 删除指定目录

```bash
# Python 脚本
python scripts/cleanup_test_files.py d:/Mycode/LLM/Cognix/tmpabc123

# 或使用批处理脚本（Windows）
scripts\cleanup_test_files.bat d:/Mycode/LLM/Cognix/tmpabc123
```

### 方式2: 清理所有临时目录

```bash
# Python 脚本
python scripts/cleanup_test_files.py --all

# 或使用批处理脚本（Windows）
scripts\cleanup_test_files.bat --all
```

### 方式3: 查看帮助

```bash
python scripts/cleanup_test_files.py --help
```

### 手动清理

也可以直接手动删除项目根目录下所有 `tmp*` 开头的目录。

## 测试检查点

| 检查点 | 说明 |
|--------|------|
| 长期记忆存储 | 验证事实、偏好、经验三类记忆正确存储 |
| Markdown文件 | 验证每个长期记忆都有对应的MD文件 |
| 短期记忆 | 验证会话级别的记忆正确管理 |
| 记忆关联 | 验证记忆之间的关联关系正确建立 |
| 记忆搜索 | 验证关键词搜索和分类搜索功能 |
| 记忆删除 | 验证删除功能正常工作 |
| 上下文生成 | 验证为Agent准备的上下文格式正确 |

## 自定义测试

你可以修改 `mock_agent_memory_test.py` 中的测试数据来适应你的需求：

```python
# 修改用户信息
result = self.agent_client.remember(
    "user_name", 
    {"name": "你的名字", "age": 30, "role": "你的角色"},
    "fact"
)
```

## 预期结果

成功运行后应该看到：
- 所有8个场景都执行完成
- 大部分操作显示 ✓ 成功
- 最后的总结显示正确的记忆统计
- 临时文件被清理

## 故障排除

### 问题: 数据库无法打开
**解决方案**: 确保临时目录有写入权限

### 问题: 导入错误
**解决方案**: 确保已正确安装依赖，检查 `sys.path` 设置

### 问题: Markdown文件未创建
**解决方案**: 检查 `config.home_path` 配置，确保目录存在

## 与实际Agent系统集成

这个Mock测试演示了如何将记忆系统集成到真实的Agent系统中：

1. 创建 `AgentMemoryClient` 实例
2. 使用 `remember()` 存储记忆
3. 使用 `recall()` 检索记忆
4. 使用 `contextualize()` 为每次对话准备上下文
5. 使用 `forget()` 删除不需要的记忆
6. 使用 `connect()` 建立记忆之间的关联

## 扩展测试建议

- 测试并发访问
- 测试大量数据存储
- 测试置信度衰减机制
- 测试记忆关联查询性能
- 测试Markdown文件编辑后的同步
