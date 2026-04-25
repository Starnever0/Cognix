import click
import json
from cognix.core.memory_system import get_memory_system


@click.command("remember")
@click.argument("heading")
@click.argument("content")
@click.option("--persistent", is_flag=True, help="保存到持久记忆")
def remember(heading, content, persistent):
    """记录一条记忆"""
    memory = get_memory_system()
    if persistent:
        memory.add_persistent_memory(heading, content)
        click.echo(json.dumps({"success": True, "type": "persistent"}, ensure_ascii=False))
    else:
        memory.add_memory(heading, content)
        click.echo(json.dumps({"success": True, "type": "daily"}, ensure_ascii=False))
