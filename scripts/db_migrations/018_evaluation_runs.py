#!/usr/bin/env python3
"""Migration 018: Add quick evaluation run records."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
sys.path.insert(0, os.path.dirname(__file__))

from cn_model_hub.config import cfg
from cn_model_hub.db import db
from _migration_utils import should_skip_due_to_future_migrations

MIGRATION_NUMBER = 18


def _table_exists(table_name: str) -> bool:
    cursor = db.cursor()
    if cfg.app.db_backend == "postgres":
        cursor.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_name=%s
            """,
            (table_name,),
        )
    else:
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,),
        )
    return cursor.fetchone() is not None


def check_migration_needed():
    return not _table_exists("evaluationrun")


def migrate_sqlite():
    cursor = db.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS evaluationrun (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            repository_id INTEGER NOT NULL,
            triggered_by_id INTEGER,
            benchmark VARCHAR(255) NOT NULL DEFAULT 'C-Eval',
            leaderboard VARCHAR(255) NOT NULL DEFAULT 'generative_llm',
            model_family VARCHAR(255) NOT NULL DEFAULT 'qwen2.5',
            dataset_repo VARCHAR(255) NOT NULL DEFAULT 'qwen_demo/c-eval',
            status VARCHAR(255) NOT NULL DEFAULT 'pending',
            total INTEGER NOT NULL DEFAULT 20,
            correct INTEGER NOT NULL DEFAULT 0,
            accuracy REAL,
            revision VARCHAR(255) NOT NULL DEFAULT 'main',
            commit_id VARCHAR(255),
            result_json TEXT,
            error TEXT,
            created_at DATETIME NOT NULL,
            started_at DATETIME,
            finished_at DATETIME,
            FOREIGN KEY(repository_id) REFERENCES repository(id) ON DELETE CASCADE,
            FOREIGN KEY(triggered_by_id) REFERENCES user(id) ON DELETE SET NULL
        )
        """
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS evaluationrun_repository_id ON evaluationrun(repository_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS evaluationrun_triggered_by_id ON evaluationrun(triggered_by_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS evaluationrun_benchmark ON evaluationrun(benchmark)")
    cursor.execute("CREATE INDEX IF NOT EXISTS evaluationrun_leaderboard ON evaluationrun(leaderboard)")
    cursor.execute("CREATE INDEX IF NOT EXISTS evaluationrun_model_family ON evaluationrun(model_family)")
    cursor.execute("CREATE INDEX IF NOT EXISTS evaluationrun_status ON evaluationrun(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS evaluationrun_accuracy ON evaluationrun(accuracy)")
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS evaluationrun_repo_created ON evaluationrun(repository_id, created_at)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS evaluationrun_board_status_accuracy ON evaluationrun(leaderboard, status, accuracy)"
    )


def migrate_postgres():
    cursor = db.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS evaluationrun (
            id SERIAL PRIMARY KEY,
            repository_id INTEGER NOT NULL REFERENCES repository(id) ON DELETE CASCADE,
            triggered_by_id INTEGER REFERENCES "user"(id) ON DELETE SET NULL,
            benchmark VARCHAR(255) NOT NULL DEFAULT 'C-Eval',
            leaderboard VARCHAR(255) NOT NULL DEFAULT 'generative_llm',
            model_family VARCHAR(255) NOT NULL DEFAULT 'qwen2.5',
            dataset_repo VARCHAR(255) NOT NULL DEFAULT 'qwen_demo/c-eval',
            status VARCHAR(255) NOT NULL DEFAULT 'pending',
            total INTEGER NOT NULL DEFAULT 20,
            correct INTEGER NOT NULL DEFAULT 0,
            accuracy DOUBLE PRECISION,
            revision VARCHAR(255) NOT NULL DEFAULT 'main',
            commit_id VARCHAR(255),
            result_json TEXT,
            error TEXT,
            created_at TIMESTAMP NOT NULL,
            started_at TIMESTAMP,
            finished_at TIMESTAMP
        )
        """
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS evaluationrun_repository_id ON evaluationrun(repository_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS evaluationrun_triggered_by_id ON evaluationrun(triggered_by_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS evaluationrun_benchmark ON evaluationrun(benchmark)")
    cursor.execute("CREATE INDEX IF NOT EXISTS evaluationrun_leaderboard ON evaluationrun(leaderboard)")
    cursor.execute("CREATE INDEX IF NOT EXISTS evaluationrun_model_family ON evaluationrun(model_family)")
    cursor.execute("CREATE INDEX IF NOT EXISTS evaluationrun_status ON evaluationrun(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS evaluationrun_accuracy ON evaluationrun(accuracy)")
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS evaluationrun_repo_created ON evaluationrun(repository_id, created_at)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS evaluationrun_board_status_accuracy ON evaluationrun(leaderboard, status, accuracy)"
    )


def run():
    db.connect(reuse_if_open=True)
    try:
        if should_skip_due_to_future_migrations(MIGRATION_NUMBER, db, cfg):
            print("Migration 018: Skipped (superseded by future migration)")
            return True

        if not check_migration_needed():
            print("Migration 018: Already applied")
            return True

        print("Migration 018: Running...")
        with db.atomic():
            if cfg.app.db_backend == "postgres":
                migrate_postgres()
            else:
                migrate_sqlite()
        print("Migration 018: [OK] Completed")
        return True
    except Exception as e:
        print(f"Migration 018: [ERROR] Failed - {e}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    success = run()
    sys.exit(0 if success else 1)
