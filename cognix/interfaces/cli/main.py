import click
from cognix.interfaces.cli.cmd_remember import remember
from cognix.interfaces.cli.cmd_recall import recall
from cognix.interfaces.cli.cmd_context import context
from cognix.interfaces.cli.cmd_dream import dream
from cognix.interfaces.cli.cmd_serve import serve


@click.group()
@click.version_option(version="0.2.0")
def cli():
    """Cognix - 非侵入式记忆系统"""
    pass


cli.add_command(remember)
cli.add_command(recall)
cli.add_command(context)
cli.add_command(dream)
cli.add_command(serve)
