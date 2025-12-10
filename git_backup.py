cat << 'EOF' > /config/git_backup.py
#!/usr/bin/env python3
import json
import yaml
from pathlib import Path
from datetime import datetime

BASE_PATH = Path("/config")
STORAGE_PATH = BASE_PATH / ".storage"
EXPORT_PATH = BASE_PATH / "dashboards_yaml"
EXPORT_PATH.mkdir(exist_ok=True)

# 1) Export STORAGE-MODE dashboards (.storage/lovelace*)
for lovelace_file in STORAGE_PATH.glob("lovelace*"):
    if lovelace_file.name == "lovelace_dashboards":
        continue

    try:
        with lovelace_file.open("r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict) and isinstance(data.get("data"), dict):
            config = data["data"].get("config", data["data"])
        else:
            config = data

        out_file = EXPORT_PATH / f"{lovelace_file.stem}.yaml"
        with out_file.open("w", encoding="utf-8") as f_out:
            yaml.dump(
                config,
                f_out,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
                width=120,
            )
    except Exception:
        pass

# 2) Export YAML-MODE dashboards from .storage/lovelace_dashboards
dashboards_registry = STORAGE_PATH / "lovelace_dashboards"
if dashboards_registry.exists():
    try:
        with dashboards_registry.open("r", encoding="utf-8") as f:
            reg = json.load(f)

        items = reg.get("data", {}).get("items", [])
        for item in items:
            if item.get("mode") != "yaml":
                continue

            filename = item.get("filename")
            if not filename:
                continue

            src = Path(filename)
            if not src.is_absolute():
                src = BASE_PATH / filename.lstrip("/")

            if not src.is_file():
                continue

            url_path = item.get("url_path") or item.get("id") or src.stem
            dst = EXPORT_PATH / f"yaml_{url_path}.yaml"

            try:
                dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
            except Exception:
                pass
    except Exception:
        pass

# 3) Write timestamp file (optional)
(BASE_PATH / ".git_last_backup").write_text(
    datetime.now().isoformat(), encoding="utf-8"
)
EOF