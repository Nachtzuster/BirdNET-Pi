#!/usr/bin/env python3
"""Refresh the managed section of disk_check_exclude.txt.

This preserves the managed behavior where one representative recording per
species is protected from purge, without depending on a web page side effect
to rebuild the file.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path


START_MARKER = "##start"
END_MARKER = "##end"


def normalize_species_dir(common_name: str) -> str:
    """Match the legacy By_Date species directory naming."""
    return common_name.replace(" ", "_").replace("'", "")


def load_existing_content(path: Path) -> str:
    if not path.exists():
        return f"{START_MARKER}\n{END_MARKER}\n"
    return path.read_text(encoding="utf-8")


def split_managed_sections(content: str) -> tuple[str, str]:
    """Return content before and from the end marker onward."""
    start_index = content.find(START_MARKER)
    end_index = content.find(END_MARKER)

    if start_index == -1 or end_index == -1 or end_index < start_index:
        return "", f"{END_MARKER}\n"

    prefix = content[:start_index]
    suffix = content[end_index:]
    return prefix, suffix


def build_managed_entries(db_path: Path) -> list[str]:
    """Return the protected recording entries for the current database."""
    if not db_path.exists():
        return []

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            WITH ranked AS (
                SELECT
                    Date,
                    Com_Name,
                    File_Name,
                    Sci_Name,
                    Confidence,
                    Time,
                    ROW_NUMBER() OVER (
                        PARTITION BY Sci_Name
                        ORDER BY Confidence DESC, Date DESC, Time DESC, File_Name DESC
                    ) AS rn
                FROM detections
            )
            SELECT Date, Com_Name, File_Name
            FROM ranked
            WHERE rn = 1
            ORDER BY Com_Name ASC
            """
        ).fetchall()
    finally:
        conn.close()

    entries: list[str] = []
    for row in rows:
        relative_path = f"{row['Date']}/{normalize_species_dir(row['Com_Name'])}/{row['File_Name']}"
        entries.append(relative_path)
        entries.append(f"{relative_path}.png")
    return entries


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    db_path = repo_root / "scripts" / "birds.db"
    exclude_path = repo_root / "scripts" / "disk_check_exclude.txt"

    prefix, suffix = split_managed_sections(load_existing_content(exclude_path))
    managed_entries = build_managed_entries(db_path)

    managed_block = START_MARKER
    if managed_entries:
        managed_block += "\n" + "\n".join(managed_entries)
    managed_block += "\n"

    exclude_path.write_text(f"{prefix}{managed_block}{suffix}", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
