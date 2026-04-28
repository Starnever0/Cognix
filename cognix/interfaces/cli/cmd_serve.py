import click
import signal
import sys


@click.command("serve")
@click.option("--dream-interval", default=24, help="Autodream间隔(小时)")
def serve(dream_interval):
    """启动Cognix后台服务(Hook + 定时整理)"""
    from cognix.hooks import HookRegistry
    from cognix.dream.scheduler import AutodreamScheduler

    click.echo("启动 Cognix 后台服务...")

    registry = HookRegistry()
    registry.start_all()

    scheduler = AutodreamScheduler()
    scheduler.start(interval_hours=dream_interval)

    click.echo(f"已启动 {len(registry.list_hooks())} 个 Hook")
    click.echo(f"Autodream 间隔: {dream_interval} 小时")
    click.echo("按 Ctrl+C 停止服务")

    def shutdown(signum, frame):
        click.echo("\n正在停止服务...")
        registry.stop_all()
        scheduler.stop()
        click.echo("服务已停止")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    import time
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown(None, None)
