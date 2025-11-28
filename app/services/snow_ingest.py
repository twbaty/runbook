# app/services/snow_ingest.py
import csv
import io

from ..extensions import db
from ..models import Ticket


def import_snow_csv(file_storage):
    """
    Import a CSV from ServiceNow.
    Handles UTF-8, CP1252 (Windows), and ISO-8859-1 automatically.
    """
    # Try UTF-8 first
    raw = file_storage.read()

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        # Fallback: Windows-1252 (most common for SNOW)
        try:
            text = raw.decode("cp1252")
        except UnicodeDecodeError:
            # Final fallback
            text = raw.decode("latin-1")

    file_storage.seek(0)  # Not strictly needed but good hygiene

    # Use io.StringIO to feed decoded text into csv.reader
    f = io.StringIO(text)

    reader = csv.DictReader(f)
    count = 0

    for row in reader:
        t = Ticket(
            number=row.get("Number"),
            short_description=row.get("Short description"),
            description=row.get("Description"),
            work_notes=row.get("Work notes"),
            resolution_notes=row.get("Resolution notes"),
            category=row.get("Category"),
            subcategory=row.get("Subcategory"),
            assignment_group=row.get("Assignment group"),
            ci=row.get("CI"),
            opened_at=row.get("Opened"),
            closed_at=row.get("Closed"),
        )
        db.session.add(t)
        count += 1

    db.session.commit()
    return count
