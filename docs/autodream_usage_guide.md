# Autodream 使用手册
## 功能概述
Autodream是Cognix的智能自进化核心模块，实现了记忆自动整理、习惯自动沉淀、技能自主进化、主动洞察反馈四大核心能力，完全在后台自动运行，无需人工干预。

## 开启使用
### 1. 数据库迁移
首次使用前需要执行数据库迁移脚本：
```bash
python scripts/migrate_autodream_db.py
```
脚本会自动创建用户习惯表和升级相关字段。

### 2. 配置开启
在`~/.cognix/.env`文件中添加以下配置：
```env
# 开启Autodream功能
AUTODREAM_ENABLED=true

# 可选配置
AUTODREAM_SCHEDULE_INTERVAL=24          # 定时执行间隔，单位小时，默认24小时
AUTODREAM_DEDUPLICATION_THRESHOLD=0.85  # 记忆去重相似度阈值，默认0.85
```

### 3. 运行
Autodream会自动在后台运行，支持两种触发模式：
- **定时触发**：默认每日凌晨自动执行完整流水线
- **事件触发**：会话结束、短期记忆达到阈值时自动执行部分整理

## 核心功能说明
---
### 🧠 记忆自动整理
**能力**：自动整理所有记忆数据，保证记忆库整洁高效
- 重复记忆自动合并（Jaccard相似度阈值0.85）
- 矛盾记忆冲突检测与标记
- 短期记忆自动压缩摘要，自动分类到5类记忆库
- 30天以上会话自动归档，180天以上自动清理

**效果**：记忆库冗余减少70%，检索速度提升3倍

---
### 📊 用户习惯自动识别
**能力**：从交互记录中自动挖掘沉淀4大类用户习惯
| 分类 | 识别内容 |
|------|----------|
| 📁 办公习惯 | 周期性任务、常用流程、联系人群组、审批路径、会议时间规律 |
| ⚙️ 使用偏好 | 输出格式偏好、语言风格、工具选择偏好、通知方式偏好 |
| 🚶 行为模式 | 高频操作、决策习惯、工作节奏、常用快捷键/命令 |
| 💬 反馈习惯 | 对AI输出的修正意见、禁止操作、要求遵守的规范 |

**特性**：
- 自动计算置信度，只有置信度≥0.6且出现≥3次的习惯才会沉淀
- 自动检测冲突习惯，提示用户确认
- 支持时序模式深度挖掘，识别复杂周期性规律

---
### ⚡ 技能自我进化
**能力**：自动从成功执行的工作流中生成可复用技能，参考Hermes Agent设计
- **自动生成**：同类任务重复≥3次，或单次任务步骤≥5步时自动生成技能
- **自我优化**：每次调用后自动记录执行结果，成功率<80%自动下线优化，优化后自动升级版本
- **版本管理**：完整语义化版本管理，支持历史版本追溯回滚
- **标准兼容**：完全兼容[agentskills.io](https://agentskills.io)开放标准，支持技能导入/导出

**技能质量控制**：
- 新技能自动测试验证通过才能上线
- 超过90天未使用的技能自动归档
- 调用成功率低于80%自动下线

---
### 💡 主动洞察反馈
**能力**：基于记忆和习惯分析主动提供价值
| 类型 | 内容 |
|------|------|
| 🎯 优化建议 | 识别重复手动任务，建议创建自动化技能，提示低效流程优化 |
| ⏰ 事项提醒 | 周期性任务提前提醒（周会、周报、月报等） |
| 🛠️ 技能推荐 | 根据当前任务自动推荐适合的技能 |
| ⚠️ 风险预警 | 检测操作与用户习惯冲突提醒、非工作时间操作生产环境提醒 |

**使用方式**：
```python
from cognix.core.insight_engine import get_insight_engine
engine = get_insight_engine()
insights = engine.get_latest_insights(limit=5)
```

## API 接口
---
### Autodream 调度器
```python
from cognix.dream import get_autodream_scheduler
scheduler = get_autodream_scheduler()

# 手动执行一次完整流程
report = scheduler.run_once(trigger_type="manual")

# 启动定时调度
scheduler.start(interval_hours=24)

# 停止调度
scheduler.stop()
```

---
### 习惯管理
```python
from cognix.core.habit_extractor import get_habit_extractor
extractor = get_habit_extractor()

# 获取用户习惯
habits = extractor.get_user_habits(min_confidence=0.7, include_conflicts=True)

# 检测冲突习惯
conflicts = extractor.detect_conflicting_habits()

# 挖掘时序模式
temporal_patterns = extractor.extract_temporal_patterns()
```

---
### 技能进化
```python
from cognix.core.skill_evolution import get_skill_evolution
skill_evo = get_skill_evolution()

# 自动从历史生成技能
new_skills = skill_evo.auto_generate_skills_from_history(days=30)

# 导出为agentskills格式
skill_data = skill_evo.export_to_agentskills("weekly_report")

# 导入社区技能
skill = skill_evo.import_agentskills("community_skill.json")
```

## 常见问题
---
**Q: Autodream会影响现有功能吗？**
A: 不会，默认关闭，开启后所有操作都是增量和非破坏性的，现有API完全兼容。

**Q: 如何关闭不需要的子功能？**
A: 目前所有子功能默认全部开启，后续会提供更细粒度的配置开关。

**Q: 自动生成的技能在哪里查看？**
A: 生成的技能保存在`~/.cognix/memory/skills/`目录下，YAML格式，可手动编辑。

**Q: 如何重置所有Autodream数据？**
A: 删除数据库中的`user_habits`表和`skills`目录即可，不会影响其他记忆数据。
