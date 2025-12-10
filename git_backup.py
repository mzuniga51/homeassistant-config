#!/usr/bin/env python3
"""
Export all Lovelace dashboards from .storage to YAML
and commit + push the full Home Assistant config to GitHub.
Also logs a history of backups.
"""

import json
import subprocess
from pathlib import Path
from datetime import datetime

import yaml


BASE_PATH = Path("/config")
STORAGE_PATH = BASE_PATH / ".storage"
EXPORT_PATH = BASE_PATH / "dashboards_yaml"
LAST_BACKUP_FILE = BASE_PATH / ".git_last_backup"
HISTORY_FILE = BASE_PATH / ".git_backup_history"
REPO_PATH = BASE_PATH


def export_dashboards() -> None:
    """Export every lovelace-related .storage file to /config/dashboards_yaml."""
    EXPORT_PATH.mkdir(exist_ok=True)

    for src in STORAGE_PATH.glob("lovelace*"):
        try:
            with src.open("r", encoding="utf-8") as f:
                data = json.load(f)

            # Try to unwrap the actual dashboard config if present
            out_data = data
            if isinstance(data, dict) and "data" in data:
                inner = data["data"]
                if isinstance(inner, dict) and "config" in inner:
                    out_data = inner["config"]
                else:
                    out_data = inner

            # Use full filename (not stem) so we keep lovelace.lovelace_XYZ separate
            out_file = EXPORT_PATH / f"{src.name}.yaml"

            with out_file.open("w", encoding="utf-8") as f_out:
                yaml.safe_dump(
                    out_data,
                    f_out,
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False,
                    width=120,
                )

        except Exception as e:
            # Log per-file error (useful for debugging a specific dashboard)
            err_file = EXPORT_PATH / f"{src.name}.error.txt"
            err_file.write_text(f"{type(e).__name__}: {e}", encoding="utf-8")

    # Timestamp for "last backup" file sensor
    LAST_BACKUP_FILE.write_text(datetime.now().isoformat(), encoding="utf-8")


def git_backup() -> None:
    """Stage, commit, push, and log a history entry."""
    now = datetime.now()
    now_iso = now.isoformat(timespec="seconds")

    # Stage everything
    subprocess.run(["git", "add", "."], cwd=REPO_PATH, check=False)

    # Commit (may be "nothing to commit")
    commit_msg = f"Backup {now.strftime('%Y-%m-%d %H:%M')}"
    commit_proc = subprocess.run(
        ["git", "commit", "-m", commit_msg],
        cwd=REPO_PATH,
        capture_output=True,
        text=True,
        check=False,
    )

    # Determine commit status
    stdout = (commit_proc.stdout or "").lower()
    stderr = (commit_proc.stderr or "").lower()

    if commit_proc.returncode == 0:
        status = "committed"
    elif "nothing to commit" in stdout + stderr:
        status = "no_changes"
    else:
        status = f"commit_error({commit_proc.returncode})"

    # Push (ignore failures but record them)
    push_proc = subprocess.run(
        ["git", "push", "origin", "main"],
        cwd=REPO_PATH,
        capture_output=True,
        text=True,
        check=False,
    )
    if push_proc.returncode != 0:
        status += f";push_error({push_proc.returncode})"

    # Get current HEAD commit (short hash)
    head_proc = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=REPO_PATH,
        capture_output=True,
        text=True,
        check=False,
    )
    commit_hash = head_proc.stdout.strip() if head_proc.returncode == 0 else "unknown"

    # Append history line
    line = f"{now_iso} | {status} | {commit_hash}"
    try:
        with HISTORY_FILE.open("a", encoding="utf-8") as hf:
            hf.write(line + "\n")
    except Exception:
        # If history logging fails, we don't want to break the backup
        pass


def main() -> None:
    export_dashboards()
    git_backup()


if __name__ == "__main__":
    main()