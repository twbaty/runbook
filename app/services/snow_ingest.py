# app/services/snow_ingest.py
import csv
from datetime import datetime
from io import TextIOWrapper
from typing import Iterable

from ..extensions import db
from ..models import Ticket

def _parse_dt(val: str) -> datetime | None:
    if not val:
        return None
    # adjust format to match your SNOW export
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(val, fmt)
        except ValueError:
            continue
    return None

def import_snow_csv(file_storage) -> int:
    """
    file_storage: Werkzeug FileStorage from Flask upload.
    Returns number of tickets imported.
    """
    stream = TextIOWrapper(file_storage.stream, encoding="utf-8")
    reader = csv.DictReader(stream)

    count = 0
    for row in reader:
        t = Ticket(
            number=row.get("Number"),
            short_description=row.get("Short description", ""),
            description=row.get("Description", ""),
            work_notes=row.get("Work notes", ""),
            resolution_notes=row.get("Close notes", ""),
            category=row.get("Category", ""),
            subcategory=row.get("Subcategory", ""),
            assignment_group=row.get("Assignment group", ""),
            ci=row.get("Configuration item", ""),
            opened_at=_parse_dt(row.get("Opened at", "")),
            closed_at=_parse_dt(row.get("Closed at", "")),
        )
        db.session.add(t)
        count += 1

    db.session.commit()
    return count
