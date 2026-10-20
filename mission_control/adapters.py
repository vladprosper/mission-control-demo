"""Bounded local JSON/CSV readers. No network calls or platform integration."""
import csv
import json
from pathlib import Path
from .store import ValidationError


def load_file(path):
    path = Path(path)
    if path.stat().st_size > 5_000_000:
        raise ValidationError("Input file exceeds 5 MB limit")
    with path.open(encoding="utf-8-sig", newline="") as stream:
        if path.suffix.lower() == ".json":
            return json.load(stream)
        if path.suffix.lower() == ".csv":
            rows = []
            reader = csv.DictReader(stream)
            if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames):
                raise ValidationError("CSV headers must be present and unique")
            for record in reader:
                if None in record or any(v is None for v in record.values()):
                    raise ValidationError("CSV row width does not match header")
                row = {k: None if v.strip() == "" else v.strip() for k, v in record.items()}
                if row.get("metric_value") is not None:
                    try:
                        row["metric_value"] = float(row["metric_value"])
                    except ValueError as exc:
                        raise ValidationError("CSV metric must be numeric or blank") from exc
                rows.append(row)
            return rows
    raise ValidationError("File reader accepts JSON or CSV only")


# Compatibility alias for the fictional walkthrough and original examples.
load_mock_file = load_file
