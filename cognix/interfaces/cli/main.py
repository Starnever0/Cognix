import click
import json
import time
import sys
from pathlib import Path
from cognix.utils.config import config as app_config
from cognix.core.preference_store import preference_store
from cognix.core.rule_engine import rule_engine
from cognix.core.scheduler import scheduler
from cognix.core.event_collector import event_collector

@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Cognix：个人工作习惯与偏好记忆引擎"""
    pass

@cli.command()
def init():
    """初始化 Cognix 配置"""
    event_collector.track_cli_command("init")
    
    click.echo("🔧 初始化 Cognix 配置...")
    config_path = app_config.home_path / ".env"
    if not config_path.exists():
        with open(config_path, "w", encoding="utf-8") as f:
            f.write("""# 飞书配置（可选）
FEISHU_APP_ID=
FEISHU_APP_SECRET=

# LLM 配置（可选，用于生成内容）
LLM_BASE_URL=
LLM_API_KEY=
LLM_MODEL=qwen3.5-35b
""")
    click.echo(f"✅ 配置文件已生成：{config_path}")
    click.echo("💡 请编辑配置文件后开始使用")

@cli.group()
def config():
    """偏好配置管理"""
    pass

@config.command("set")
@click.argument("key")
@click.argument("value")
@click.option("--weight", default=1.0, type=float, help="偏好权重，0-1之间，默认1.0")
def set_config(key, value, weight):
    """设置偏好：cognix config set report_format table"""
    event_collector.track_cli_command("config set", {"key": key, "value": value, "weight": weight})
    
    try:
        # 尝试解析JSON格式的值
        value_dict = json.loads(value) if value.startswith("{") or value.startswith("[") else {"value": value}
    except:
        value_dict = {"value": value}
    
    old_value = preference_store.set(key, value_dict, weight)
    event_collector.track_preference_change(key, old_value, value_dict)
    
    click.echo(f"✅ 已设置偏好：{key} = {json.dumps(value_dict, ensure_ascii=False)}")
    if old_value:
        click.echo(f"ℹ️ 旧值：{json.dumps(old_value, ensure_ascii=False)}")

@config.command("list")
def list_config():
    """列出所有偏好"""
    event_collector.track_cli_command("config list")
    
    prefs = preference_store.list()
    if not prefs:
        click.echo("ℹ️ 暂无偏好设置")
        return
    
    click.echo("📋 偏好列表：")
    for pref in prefs:
        click.echo(f"  {pref['key']}: {json.dumps(pref['value'], ensure_ascii=False)} (权重: {pref['weight']})")
        click.echo(f"    创建时间: {pref['created_at']}，更新时间: {pref['updated_at']}")

@config.command("delete")
@click.argument("key")
def delete_config(key):
    """删除指定偏好：cognix config delete test_key"""
    event_collector.track_cli_command("config delete", {"key": key})
    
    success = preference_store.delete(key)
    if success:
        click.echo(f"✅ 已删除偏好：{key}")
    else:
        click.echo(f"❌ 偏好不存在：{key}")

@cli.group()
def rule():
    """规则管理"""
    pass

@rule.command("list")
@click.option("--status", default=None, help="过滤规则状态：pending/active/disabled")
def list_rules(status):
    """列出所有规则"""
    event_collector.track_cli_command("rule list", {"status": status})
    
    rules = rule_engine.store.list_rules(status)
    if not rules:
        click.echo("ℹ️ 暂无规则")
        return
    
    status_colors = {
        "pending": "yellow",
        "active": "green",
        "disabled": "red"
    }
    
    click.echo("📋 规则列表：")
    for rule in rules:
        color = status_colors.get(rule["status"], "white")
        status_text = click.style(f"[{rule['status']}]", fg=color)
        click.echo(f"  [{rule['id']}] {rule['name']} {status_text}")
        click.echo(f"    触发条件: {rule['trigger']}")
        click.echo(f"    执行动作: {json.dumps(rule['action'], ensure_ascii=False)}")
        click.echo(f"    创建时间: {rule['created_at']}")
        click.echo()

@rule.command("confirm")
@click.argument("rule_id", type=int)
def confirm_rule(rule_id):
    """确认待激活的规则：cognix rule confirm 1"""
    event_collector.track_cli_command("rule confirm", {"rule_id": rule_id})
    
    success = rule_engine.confirm_rule(rule_id)
    if success:
        scheduler.reload_rules()
        event_collector.track_user_feedback(rule_id, "confirm")
        click.echo(f"✅ 规则 {rule_id} 已激活")
    else:
        click.echo(f"❌ 规则激活失败：规则不存在或状态不是待确认")

@rule.command("reject")
@click.argument("rule_id", type=int)
def reject_rule(rule_id):
    """拒绝待激活的规则：cognix rule reject 1"""
    event_collector.track_cli_command("rule reject", {"rule_id": rule_id})
    
    success = rule_engine.reject_rule(rule_id)
    if success:
        event_collector.track_user_feedback(rule_id, "reject")
        click.echo(f"✅ 规则 {rule_id} 已拒绝并禁用")
    else:
        click.echo(f"❌ 规则拒绝失败：规则不存在或状态不是待确认")

@rule.command("disable")
@click.argument("rule_id", type=int)
def disable_rule(rule_id):
    """禁用已激活的规则：cognix rule disable 1"""
    event_collector.track_cli_command("rule disable", {"rule_id": rule_id})
    
    success = rule_engine.disable_rule(rule_id)
    if success:
        scheduler.reload_rules()
        click.echo(f"✅ 规则 {rule_id} 已禁用")
    else:
        click.echo(f"❌ 规则禁用失败：规则不存在或状态不是已激活")

@rule.command("enable")
@click.argument("rule_id", type=int)
def enable_rule(rule_id):
    """启用已禁用的规则：cognix rule enable 1"""
    event_collector.track_cli_command("rule enable", {"rule_id": rule_id})
    
    success = rule_engine.enable_rule(rule_id)
    if success:
        scheduler.reload_rules()
        click.echo(f"✅ 规则 {rule_id} 已启用")
    else:
        click.echo(f"❌ 规则启用失败：规则不存在或状态不是已禁用")

@rule.command("create-weekly")
@click.option("--time", default="15:55", help="触发时间，格式 HH:MM，默认 15:55")
@click.option("--day", default="fri", help="触发星期：mon/tue/wed/thu/fri/sat/sun，默认周五（fri）")
def create_weekly_rule(time, day):
    """创建周报规则：cognix rule create-weekly --time 18:00 --day fri"""
    event_collector.track_cli_command("rule create-weekly", {"time": time, "day": day})
    
    rule_id = rule_engine.generate_weekly_report_rule(time, day)
    click.echo(f"✅ 周报规则已创建，ID：{rule_id}")
    click.echo("💡 请运行 cognix rule confirm 激活规则")

@cli.command()
def weekly_report():
    """手动生成周报"""
    event_collector.track_cli_command("weekly_report")
    
    fmt = preference_store.get_report_format()
    receiver = preference_store.get_weekly_report_receiver()
    
    click.echo(f"📝 正在生成 {fmt} 格式周报...")
    # TODO: 后续接入LLM生成周报内容
    click.echo("✅ 周报生成完成")
    if receiver:
        click.echo(f"📤 默认接收人：{receiver}")
    else:
        click.echo("ℹ️ 未配置接收人，可通过 cognix config set weekly_report_receiver \"Leader A\" 设置")

@cli.command()
def suggest():
    """获取智能建议"""
    event_collector.track_cli_command("suggest")
    
    pending_rules = rule_engine.get_pending_rules()
    if pending_rules:
        click.echo("💡 待确认的规则建议：")
        for rule in pending_rules:
            click.echo(f"  [{rule['id']}] {rule['name']}")
            click.echo(f"    触发条件: {rule['trigger']}")
            click.echo(f"    执行动作: {json.dumps(rule['action'], ensure_ascii=False)}")
            click.echo()
    
    # 统计高频行为建议
    recent_events = event_collector.store.get_events(limit=20)
    cli_commands = [e["data"]["command"] for e in recent_events if e["type"] == "cli_command"]
    if cli_commands:
        from collections import Counter
        top_commands = Counter(cli_commands).most_common(3)
        click.echo("🔍 最近高频使用命令：")
        for cmd, count in top_commands:
            click.echo(f"  {cmd}: {count} 次")

@cli.command()
def start():
    """启动 Cognix 后台服务"""
    event_collector.track_cli_command("start")
    
    click.echo("🚀 启动 Cognix 服务...")
    
    # 注册动作处理器
    def handle_weekly_report(action):
        click.echo("\n" + "="*60)
        click.echo("🔔 【周报提醒】")
        click.echo(f"已按你偏好的 {action['format']} 格式生成周报草稿")
        if action.get("receiver"):
            click.echo(f"默认接收人：{action['receiver']}")
        click.echo("="*60 + "\n")
    
    def handle_meeting_reminder(action):
        click.echo("\n" + "="*60)
        click.echo("⏰ 【会议提醒】")
        click.echo(f"距离会议还有 {action['before_minutes']} 分钟")
        click.echo(f"会议时间：{action['meeting_time']}")
        if action.get("content"):
            click.echo(f"准备内容：{action['content']}")
        click.echo("="*60 + "\n")
    
    scheduler.register_action_handler("weekly_report", handle_weekly_report)
    scheduler.register_action_handler("meeting_reminder", handle_meeting_reminder)
    
    scheduler.start()
    
    active_rules = rule_engine.get_active_rules()
    click.echo(f"✅ 服务已启动，当前有 {len(active_rules)} 条激活规则")
    jobs = scheduler.get_jobs()
    for job in jobs:
        if job["next_run_time"]:
            click.echo(f"  - {job['name']}，下次执行：{job['next_run_time']}")
    
    click.echo("\n💡 按 Ctrl+C 停止服务")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        scheduler.shutdown()
        click.echo("\n👋 服务已停止")

@cli.command()
def status():
    """查看服务状态"""
    event_collector.track_cli_command("status")
    
    active_rules = rule_engine.get_active_rules()
    pending_rules = rule_engine.get_pending_rules()
    
    click.echo("📊 Cognix 状态：")
    click.echo(f"  激活规则数量：{len(active_rules)}")
    click.echo(f"  待确认规则数量：{len(pending_rules)}")
    
    # 统计事件数量
    total_events = 0
    for file in app_config.events_path.glob("*.jsonl"):
        with open(file, "r", encoding="utf-8") as f:
            total_events += len(f.readlines())
    click.echo(f"  累计事件数量：{total_events}")
    
    if scheduler.scheduler.running:
        jobs = scheduler.get_jobs()
        click.echo(f"  运行中任务数量：{len(jobs)}")

if __name__ == "__main__":
    cli()
