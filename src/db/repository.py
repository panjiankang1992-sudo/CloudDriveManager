"""CRUD repository for cloud_drive_configs table."""

from typing import List, Optional, Union

from src.core.logger import get_logger
from src.core import encryption as enc
from src.db.database import Database
from src.db.schemas import (
    CloudDriveConfigCreate,
    CloudDriveConfigUpdate,
    CloudDriveConfigResponse,
    CloudDriveConfigApplyResponse,
)

logger = get_logger("db.repository")


class CloudDriveConfigRepository:
    """CRUD operations on cloud_drive_configs table.

    Works with Database singleton.
    """

    TABLE = "cloud_drive_configs"

    def __init__(self, db: Database):
        self._db = db

    # ── Internal helpers ────────────────────────────────────────────────────────

    def _row_to_response(self, row: dict) -> CloudDriveConfigResponse:
        """Convert a DB row dict to CloudDriveConfigResponse (never exposes password)."""
        return CloudDriveConfigResponse(
            drive_type=row["drive_type"],
            remote_name=row["remote_name"],
            drive_type_variant=row["drive_type_variant"],
            host_endpoint=row.get("host_endpoint"),
            username=row.get("username"),
            password_set=bool(row.get("encrypted_password")),
            is_enabled=bool(row.get("is_enabled", True)),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )

    def _encrypt_password(self, plaintext: Optional[str]) -> Optional[str]:
        if not plaintext:
            return None
        return enc.encrypt(plaintext)

    def _decrypt_password(self, ciphertext: Optional[str]) -> Optional[str]:
        if not ciphertext:
            return None
        try:
            return enc.decrypt(ciphertext)
        except Exception:
            logger.error("Failed to decrypt password for %s", ciphertext[:20])
            return None

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def list_all(self) -> List[CloudDriveConfigResponse]:
        """List all cloud drive configs."""
        rows = self._db.fetch_all(f"SELECT * FROM {self.TABLE} ORDER BY drive_type")
        return [self._row_to_response(row) for row in rows]

    def get_by_drive_type(self, drive_type: str) -> Optional[CloudDriveConfigResponse]:
        """Get a single config by drive_type."""
        row = self._db.fetch_one(f"SELECT * FROM {self.TABLE} WHERE drive_type = %s", (drive_type,))
        return self._row_to_response(row) if row else None

    def get_by_drive_type_raw(self, drive_type: str) -> Optional[dict]:
        """Get raw DB row (includes encrypted_password) for internal use."""
        return self._db.fetch_one(f"SELECT * FROM {self.TABLE} WHERE drive_type = %s", (drive_type,))

    def create(self, data: CloudDriveConfigCreate) -> CloudDriveConfigResponse:
        """Create a new cloud drive config."""
        encrypted = self._encrypt_password(data.password)
        self._db.execute(
            f"""INSERT INTO {self.TABLE}
            (drive_type, remote_name, drive_type_variant, host_endpoint,
             username, encrypted_password, is_enabled)
            VALUES (%s,%s,%s,%s,%s,%s,TRUE)""",
            (data.drive_type, data.remote_name, data.drive_type_variant,
             data.host_endpoint, data.username, encrypted),
        )
        logger.info("Created cloud drive config: %s", data.drive_type)
        return self.get_by_drive_type(data.drive_type)

    def update(self, drive_type: str, data: CloudDriveConfigUpdate) -> Optional[CloudDriveConfigResponse]:
        """Update an existing cloud drive config."""
        sets = []
        params = []
        if data.remote_name is not None:
            sets.append("remote_name=%s"); params.append(data.remote_name)
        if data.drive_type_variant is not None:
            sets.append("drive_type_variant=%s"); params.append(data.drive_type_variant)
        if data.host_endpoint is not None:
            sets.append("host_endpoint=%s"); params.append(data.host_endpoint)
        if data.username is not None:
            sets.append("username=%s"); params.append(data.username)
        if data.password is not None:
            sets.append("encrypted_password=%s"); params.append(self._encrypt_password(data.password))
        if data.is_enabled is not None:
            sets.append("is_enabled=%s"); params.append(data.is_enabled)
        if not sets:
            return self.get_by_drive_type(drive_type)
        params.append(drive_type)
        self._db.execute(f"UPDATE {self.TABLE} SET {','.join(sets)} WHERE drive_type=%s", tuple(params))
        logger.info("Updated cloud drive config: %s", drive_type)
        return self.get_by_drive_type(drive_type)

    def delete(self, drive_type: str) -> bool:
        """Delete a cloud drive config. Returns True if deleted."""
        rowcount = self._db.execute(f"DELETE FROM {self.TABLE} WHERE drive_type=%s", (drive_type,))
        logger.info("Deleted cloud drive config: %s", drive_type)
        return rowcount > 0

    def get_enabled_configs(self) -> List[dict]:
        """Get all enabled configs with decrypted passwords (for rclone config)."""
        rows = self._db.fetch_all(f"SELECT * FROM {self.TABLE} WHERE is_enabled=TRUE")
        result = []
        for row in rows:
            row = dict(row)
            if row.get("encrypted_password"):
                row["password_plaintext"] = self._decrypt_password(row["encrypted_password"])
            else:
                row["password_plaintext"] = None
            result.append(row)
        return result


def create_tables(db: Database) -> None:
    """Create the cloud_drive_configs table if it doesn't exist."""
    db.execute("""
        CREATE TABLE IF NOT EXISTS cloud_drive_configs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            drive_type VARCHAR(32) NOT NULL UNIQUE,
            remote_name VARCHAR(128) NOT NULL,
            drive_type_variant VARCHAR(32) NOT NULL,
            host_endpoint VARCHAR(512) NULL,
            username VARCHAR(256) NULL,
            encrypted_password VARCHAR(512) NULL,
            is_enabled BOOLEAN DEFAULT TRUE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_drive_type (drive_type)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    logger.info("Table cloud_drive_configs ensured")
