import click
import json


@click.command("dream")
def dream():
    """手动触发记忆整理(Autodream)"""
    from cognix.dream.scheduler import AutodreamScheduler
    scheduler = AutodreamScheduler()
    report = scheduler.run_once()
    click.echo(json.dumps(report, ensure_ascii=False, indent=2))
