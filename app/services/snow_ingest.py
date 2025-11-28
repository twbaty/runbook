# app/services/snow_ingest.py
import csv
import io
from datetime import datetime

from ..extensions import db
from ..models import Ticket


def import_snow_csv(file_storage):
    """
    Robust CSV loader for ServiceNow exports.
    Handles:
      - Windows-1252 encoding
      - bad bytes
      - extremely large files
      - missing columns
    """
    # Read entire file safely (very fast even for 50MB)
    raw_bytes = file_storage.read()

    # Decode using Windows-1252 with ignore fallback
    text = raw_bytes.decode("cp1252", errors="ignore")

    # Use csv.DictReader on the decoded text
    reader = csv.DictReader(io.StringIO(text))

    count = 0
    for row in reader:
        try:
            t = Ticket(
                number=row.get("Number") or row.get("number"),
                short_description=row.get("Short description") or "",
                description=row.get("Description") or "",
                work_notes=row.get("Work notes") or "",
                resolution_notes=row.get("Close notes") or "",
                category=row.get("Category") or "",
                subcategory=row.get("Subcategory") or "",
                assignment_group=row.get("Assignment group") or "",
                ci=row.get("Configuration item") or "",
                opened_at=_parse_date(row.get("Opened")),
                closed_at=_parse_date(row.get("Closed"))
            )
            db.session.add(t)
            count += 1

        except Exception as e:
            print("ROW ERROR:", e, row)
            continue

    db.session.commit()
    return count


def _parse_date(s):
    """Parses ServiceNow datetime strings, returns datetime or None."""
    if not s:
        return None

    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            pass

    return None
