import click
from cognix.core.memory_system import get_memory_system


@click.command("context")
@click.option("--days", default=1, help="回溯天数")
def context(days):
    """获取近期上下文"""
    memory = get_memory_system()
    result = memory.get_daily_context(days)
    click.echo(result)
