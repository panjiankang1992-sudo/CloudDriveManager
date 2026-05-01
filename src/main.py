"""Command-line entry point for CloudDriveManager.

Usage:
    python main.py              # dev mode (config_dev.yaml)
    python main.py --prod       # production mode (config_prod.yaml)
    python main.py init-db      # initialize database tables
    python main.py --help
"""

from __future__ import annotations

import argparse
import sys

from src.core.config import Config
from src.core.logger import get_logger, setup_logger

logger = get_logger("main")


def cmd_init_db() -> None:
    """Initialize database tables."""
    print("Initializing database tables...")
    try:
        from src.db.init_db import run as _run
        _run()
        print("Database initialized successfully.")
    except Exception as e:
        print(f"Database initialization failed: {e}")
        sys.exit(1)


def cmd_run(prod: bool = False) -> None:
    """Start the HTTP API server."""
    import uvicorn
    from typing import Any

    env = "prod" if prod else "dev"
    cfg: Any = Config.get()  # type: ignore[reportCallIssue]
    setup_logger("app", log_file=cfg.log_file, level=cfg.log_level)

    logger.info(f"Starting CloudDriveManager (env={env}) on {cfg.api_host}:{cfg.api_port}")

    uvicorn.run(
        "src.app:app",
        host=cfg.api_host,
        port=cfg.api_port,
        reload=(env == "dev"),
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CloudDriveManager — Universal cloud drive file operations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--prod",
        action="store_true",
        help="Use config_prod.yaml instead of config_dev.yaml",
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=["init-db", "run"],
        help="Command to run (default: run)",
    )

    args = parser.parse_args()
    cmd = args.command or "run"

    if cmd == "init-db":
        cmd_init_db()
    else:
        cmd_run(prod=args.prod)


if __name__ == "__main__":
    main()