import click
import json
from cognix.core.memory_system import get_memory_system


@click.command("recall")
@click.argument("query")
@click.option("--limit", default=10, help="返回结果数量")
@click.option("--source", default=None, help="来源过滤(memory/persistent)")
def recall(query, limit, source):
    """搜索记忆"""
    memory = get_memory_system()
    results = memory.search_memory(query, limit, source)
    click.echo(json.dumps(results, ensure_ascii=False, indent=2))
