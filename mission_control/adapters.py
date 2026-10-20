"""Bounded local JSON/CSV readers. No network calls or platform integration."""
import csv
import json
from pathlib import Path
from .store import ValidationError


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValidationError(f"Duplicate JSON field: {key}")
        result[key] = value
    return result


def load_file(path):
    path = Path(path)
    if path.stat().st_size > 5_000_000:
        raise ValidationError("Input file exceeds 5 MB limit")
    with path.open(encoding="utf-8-sig", newline="") as stream:
        if path.suffix.lower() == ".json":
            return json.load(stream, object_pairs_hook=unique_object)
        if path.suffix.lower() == ".csv":
            rows = []
            reader = csv.DictReader(stream, strict=True)
            try:
                headers = reader.fieldnames
            except csv.Error as exc:
                raise ValidationError(f"Malformed CSV header: {exc}") from exc
            if not headers or len(set(headers)) != len(headers):
                raise ValidationError("CSV headers must be present and unique")
            for record in csv_records(reader):
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


def csv_records(reader):
    try:
        yield from reader
    except csv.Error as exc:
        raise ValidationError(f"Malformed CSV near line {reader.line_num}: {exc}") from exc


# Compatibility alias for the fictional walkthrough and original examples.
load_mock_file = load_file
