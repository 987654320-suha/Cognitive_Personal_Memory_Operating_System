# 📁 LOCATION: backend/scripts/export_memories.py
"""
export_memories.py
==================
Exports all memories from the DB to JSON or CSV.
Useful for backups, data migration, and research analysis.

Usage:
    python scripts/export_memories.py --format json --output data/export.json
    python scripts/export_memories.py --format csv  --output data/export.csv
"""

from __future__ import annotations
import argparse
import json
import csv
from pathlib import Path
from datetime import datetime


def export_json(memories: list[dict], output_path: str):
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    export_data = {
        "exported_at": datetime.utcnow().isoformat(),
        "total":       len(memories),
        "memories":    memories,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)
    print(f"[Export] JSON saved to: {output_path} ({len(memories)} memories)")


def export_csv(memories: list[dict], output_path: str):
    if not memories:
        print("[Export] No memories to export.")
        return

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    fields = ["id", "title", "description", "source", "file_type",
              "date", "location", "importance_score", "access_count"]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(memories)

    print(f"[Export] CSV saved to: {output_path} ({len(memories)} rows)")


def run_export(fmt: str, output: str):
    from backend.app.services.database_service import get_all_memories
    memories = get_all_memories()

    # Strip embeddings (too large for export)
    for m in memories:
        m.pop("embedding", None)

    if fmt == "json":
        export_json(memories, output)
    elif fmt == "csv":
        export_csv(memories, output)
    else:
        print(f"[Export] Unknown format: {fmt}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--format", choices=["json", "csv"], default="json")
    parser.add_argument("--output", default=f"data/export_{datetime.utcnow().strftime('%Y%m%d')}.json")
    args = parser.parse_args()
    run_export(args.format, args.output)
