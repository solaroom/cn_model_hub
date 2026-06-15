#!/usr/bin/env python3
"""Migration 017: Add repository MLflow binding fields."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
sys.path.insert(0, os.path.dirname(__file__))

from kohakuhub.config import cfg
from kohakuhub.db import db
from _migration_utils import check_column_exists, should_skip_due_to_future_migrations

MIGRATION_NUMBER = 17


def is_applied(db, cfg):
    """Check if this migration has been applied."""
    return all(
        (
            check_column_exists(db, cfg, "repository", "mlflow_enabled"),
            check_column_exists(db, cfg, "repository", "mlflow_experiment_name"),
            check_column_exists(db, cfg, "repository", "mlflow_experiment_id"),
            check_column_exists(db, cfg, "repository", "mlflow_last_synced_at"),
        )
    )


def check_migration_needed():
    return not is_applied(db, cfg)


def migrate_sqlite():
    cursor = db.cursor()
    cursor.execute(
        "ALTER TABLE repository ADD COLUMN mlflow_enabled INTEGER DEFAULT 0 NOT NULL"
    )
    cursor.execute(
        "ALTER TABLE repository ADD COLUMN mlflow_experiment_name VARCHAR(255) DEFAULT NULL"
    )
    cursor.execute(
        "ALTER TABLE repository ADD COLUMN mlflow_experiment_id VARCHAR(255) DEFAULT NULL"
    )
    cursor.execute(
        "ALTER TABLE repository ADD COLUMN mlflow_last_synced_at DATETIME DEFAULT NULL"
    )


def migrate_postgres():
    cursor = db.cursor()
    cursor.execute(
        "ALTER TABLE repository ADD COLUMN mlflow_enabled BOOLEAN DEFAULT FALSE NOT NULL"
    )
    cursor.execute(
        "ALTER TABLE repository ADD COLUMN mlflow_experiment_name VARCHAR(255) DEFAULT NULL"
    )
    cursor.execute(
        "ALTER TABLE repository ADD COLUMN mlflow_experiment_id VARCHAR(255) DEFAULT NULL"
    )
    cursor.execute(
        "ALTER TABLE repository ADD COLUMN mlflow_last_synced_at TIMESTAMP DEFAULT NULL"
    )


def run():
    db.connect(reuse_if_open=True)
    try:
        if should_skip_due_to_future_migrations(MIGRATION_NUMBER, db, cfg):
            print("Migration 017: Skipped (superseded by future migration)")
            return True

        if not check_migration_needed():
            print("Migration 017: Already applied")
            return True

        print("Migration 017: Running...")
        with db.atomic():
            if cfg.app.db_backend == "postgres":
                migrate_postgres()
            else:
                migrate_sqlite()
        print("Migration 017: [OK] Completed")
        return True
    except Exception as e:
        print(f"Migration 017: [ERROR] Failed - {e}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    success = run()
    sys.exit(0 if success else 1)
