#!/usr/bin/env python3
"""Migration 016: Add repository discussions."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
sys.path.insert(0, os.path.dirname(__file__))

from kohakuhub.config import cfg
from kohakuhub.db import db
from _migration_utils import check_table_exists, should_skip_due_to_future_migrations

MIGRATION_NUMBER = 16


def is_applied(db, cfg):
    """Check if this migration has been applied."""
    return check_table_exists(db, "discussion") and check_table_exists(
        db, "discussioncomment"
    )


def check_migration_needed():
    return not is_applied(db, cfg)


def migrate_sqlite():
    cursor = db.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS discussion (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            repository_id INTEGER NOT NULL,
            author_id INTEGER,
            title VARCHAR(255) NOT NULL,
            body TEXT NOT NULL,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            FOREIGN KEY (repository_id) REFERENCES repository(id) ON DELETE CASCADE,
            FOREIGN KEY (author_id) REFERENCES user(id) ON DELETE SET NULL
        )
        """
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS discussion_repository_id ON discussion(repository_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS discussion_author_id ON discussion(author_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS discussion_repository_created_at ON discussion(repository_id, created_at)"
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS discussioncomment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            discussion_id INTEGER NOT NULL,
            author_id INTEGER,
            body TEXT NOT NULL,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            FOREIGN KEY (discussion_id) REFERENCES discussion(id) ON DELETE CASCADE,
            FOREIGN KEY (author_id) REFERENCES user(id) ON DELETE SET NULL
        )
        """
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS discussioncomment_discussion_id ON discussioncomment(discussion_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS discussioncomment_author_id ON discussioncomment(author_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS discussioncomment_discussion_created_at ON discussioncomment(discussion_id, created_at)"
    )


def migrate_postgres():
    cursor = db.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS discussion (
            id SERIAL PRIMARY KEY,
            repository_id INTEGER NOT NULL REFERENCES repository(id) ON DELETE CASCADE,
            author_id INTEGER REFERENCES "user"(id) ON DELETE SET NULL,
            title VARCHAR(255) NOT NULL,
            body TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL,
            updated_at TIMESTAMP NOT NULL
        )
        """
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS discussion_repository_id ON discussion(repository_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS discussion_author_id ON discussion(author_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS discussion_repository_created_at ON discussion(repository_id, created_at)"
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS discussioncomment (
            id SERIAL PRIMARY KEY,
            discussion_id INTEGER NOT NULL REFERENCES discussion(id) ON DELETE CASCADE,
            author_id INTEGER REFERENCES "user"(id) ON DELETE SET NULL,
            body TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL,
            updated_at TIMESTAMP NOT NULL
        )
        """
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS discussioncomment_discussion_id ON discussioncomment(discussion_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS discussioncomment_author_id ON discussioncomment(author_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS discussioncomment_discussion_created_at ON discussioncomment(discussion_id, created_at)"
    )


def run():
    db.connect(reuse_if_open=True)
    try:
        if should_skip_due_to_future_migrations(MIGRATION_NUMBER, db, cfg):
            print("Migration 016: Skipped (superseded by future migration)")
            return True

        if not check_migration_needed():
            print("Migration 016: Already applied")
            return True

        print("Migration 016: Running...")
        with db.atomic():
            if cfg.app.db_backend == "postgres":
                migrate_postgres()
            else:
                migrate_sqlite()
        print("Migration 016: [OK] Completed")
        return True
    except Exception as e:
        print(f"Migration 016: [ERROR] Failed - {e}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    success = run()
    sys.exit(0 if success else 1)
