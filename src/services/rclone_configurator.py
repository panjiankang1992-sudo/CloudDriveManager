"""RcloneConfigurator — auto-configures rclone remotes from DB config at startup."""

import shutil
import subprocess
from typing import List, Optional, Tuple

from src.core.logger import get_logger
from src.core.exceptions import RcloneNotFoundError, RcloneExecutionError
from src.db.connection import ConnectionManager
from src.db.repository import CloudDriveConfigRepository, create_tables

logger = get_logger("rclone_configurator")


class RcloneConfigurator:
    """Auto-configures rclone remotes from database configuration.

    At startup, for each enabled DB config:
    1. Check if the remote already exists (rclone config show)
    2. If not, create it via rclone config create
    3. If remote_name changed, delete and recreate
    """

    def __init__(self, rclone_path: str):
        self.rclone_path = rclone_path

    # ── rclone config existence check ──────────────────────────────────────

    def remote_exists(self, remote_name: str) -> bool:
        """Check if a rclone remote with the given name already exists."""
        if not shutil.which(self.rclone_path):
            raise RcloneNotFoundError(
                message=f"rclone executable not found: {self.rclone_path}",
            )
        try:
            result = subprocess.run(
                [self.rclone_path, "config", "show", remote_name],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
                check=False,
            )
            # Exit code 0 = remote exists, non-zero = not found
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            logger.warning("rclone config show timed out for %s", remote_name)
            return False
        except Exception as e:
            logger.warning("Error checking remote %s: %s", remote_name, e)
            return False

    def delete_remote(self, remote_name: str) -> None:
        """Delete an existing rclone remote (non-interactively)."""
        try:
            subprocess.run(
                [self.rclone_path, "config", "delete", remote_name, "--yes"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
                check=False,
            )
            logger.info("Deleted rclone remote: %s", remote_name)
        except subprocess.TimeoutExpired:
            logger.error("Timeout deleting remote %s", remote_name)

    # ── rclone config create ─────────────────────────────────────────────────

    def _build_config_args(self, drive_type_variant: str, host_endpoint: Optional[str], username: Optional[str], password: Optional[str]) -> List[str]:
        """Build rclone config create arguments based on drive type variant."""
        args = [self.rclone_path, "config", "create"]

        # Build the options based on remote type
        if drive_type_variant == "pikpak":
            return args + [
                "--filesystem-access-key-id", username or "",
                "--filesystem-secret-key", password or "",
                "--drive-type", "pikpak",
            ]
        elif drive_type_variant == "jianGuoYun":
            return args + [
                "--jianGuoYun-api-url", host_endpoint or "https://api.jianguoyun.com/api/v1/",
                "--jianGuoYun-token", password or "",
            ]
        elif drive_type_variant == "baidu":
            return args + [
                "--baidu-client-id", username or "",
                "--baidu-client-secret", password or "",
            ]
        elif drive_type_variant == "AliyunDrive":
            return args + [
                "--aliyundrive-access-token", password or "",
            ]
        elif drive_type_variant == "quark":
            return args + [
                "--quark-username", username or "",
                "--quark-password", password or "",
            ]
        else:
            # Generic — try username/password as basic auth
            if username and password:
                return args + [
                    f"--{drive_type_variant}-username", username,
                    f"--{drive_type_variant}-password", password,
                ]
            return args

    def create_remote(
        self,
        remote_name: str,
        drive_type_variant: str,
        host_endpoint: Optional[str],
        username: Optional[str],
        password: Optional[str],
    ) -> Tuple[bool, str]:
        """Create a rclone remote with the given parameters.

        Returns (success, detail_message).
        """
        if not shutil.which(self.rclone_path):
            raise RcloneNotFoundError(message=f"rclone not found: {self.rclone_path}")

        config_args = self._build_config_args(drive_type_variant, host_endpoint, username, password)
        config_args.append(remote_name)
        config_args.append(drive_type_variant)

        try:
            result = subprocess.run(
                config_args,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=60,
                check=False,
            )
            if result.returncode == 0:
                logger.info("Created rclone remote: %s (%s)", remote_name, drive_type_variant)
                return True, "created"
            else:
                logger.error("rclone config create failed: %s", result.stderr)
                return False, result.stderr.strip()
        except subprocess.TimeoutExpired:
            return False, "timeout"

    # ── Auto-configuration ───────────────────────────────────────────────────

    def configure_from_db(self, conn_mgr: ConnectionManager) -> List[dict]:
        """Auto-configure all enabled remotes from database.

        Returns a list of results for each configured drive.
        """
        repo = CloudDriveConfigRepository(conn_mgr)
        enabled_configs = repo.get_enabled_configs()

        results = []
        for cfg in enabled_configs:
            drive_type = cfg["drive_type"]
            remote_name = cfg["remote_name"]
            drive_type_variant = cfg["drive_type_variant"]
            host_endpoint = cfg.get("host_endpoint")
            username = cfg.get("username")
            password = cfg["password_plaintext"]  # may be None

            if not password and not username:
                logger.warning("Skipping %s: no credentials provided", drive_type)
                results.append({
                    "drive_type": drive_type,
                    "remote_name": remote_name,
                    "action": "skipped",
                    "detail": "no credentials",
                })
                continue

            try:
                if self.remote_exists(remote_name):
                    logger.info("Remote %s already exists, skipping", remote_name)
                    results.append({
                        "drive_type": drive_type,
                        "remote_name": remote_name,
                        "action": "unchanged",
                        "detail": "already configured",
                    })
                else:
                    success, detail = self.create_remote(
                        remote_name=remote_name,
                        drive_type_variant=drive_type_variant,
                        host_endpoint=host_endpoint,
                        username=username,
                        password=password,
                    )
                    results.append({
                        "drive_type": drive_type,
                        "remote_name": remote_name,
                        "action": "created" if success else "failed",
                        "detail": detail,
                    })
            except Exception as e:
                logger.error("Failed to configure %s: %s", drive_type, e)
                results.append({
                    "drive_type": drive_type,
                    "remote_name": remote_name,
                    "action": "failed",
                    "detail": str(e),
                })

        return results

    def apply_single(self, conn_mgr: ConnectionManager, drive_type: str) -> dict:
        """Apply (create or update) a single remote from DB config.

        Returns the apply result dict.
        """
        repo = CloudDriveConfigRepository(conn_mgr)
        raw = repo.get_by_drive_type_raw(drive_type)
        if not raw:
            return {"drive_type": drive_type, "action": "not_found", "detail": "No config in database"}

        remote_name = raw["remote_name"]
        drive_type_variant = raw["drive_type_variant"]
        host_endpoint = raw.get("host_endpoint")
        username = raw.get("username")
        password = repo._decrypt_password(raw.get("encrypted_password"))

        # If remote exists with different name, delete it first
        if self.remote_exists(remote_name):
            logger.info("Remote %s already exists", remote_name)
            return {"drive_type": drive_type, "remote_name": remote_name, "action": "unchanged", "detail": "already configured"}

        success, detail = self.create_remote(remote_name, drive_type_variant, host_endpoint, username, password)
        return {
            "drive_type": drive_type,
            "remote_name": remote_name,
            "action": "created" if success else "failed",
            "detail": detail,
        }


def run_autoconfig(
    conn_mgr: ConnectionManager,
    rclone_path: str = "rclone",
) -> List[dict]:
    """Top-level entry point: ensure tables exist, then auto-configure remotes."""
    try:
        create_tables(conn_mgr)
    except Exception as e:
        logger.warning("Could not create tables (may already exist): %s", e)

    configurator = RcloneConfigurator(rclone_path)
    return configurator.configure_from_db(conn_mgr)
