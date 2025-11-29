# app/services/snow_ingest.py
import csv
import io
from datetime import datetime

from ..extensions import db
from ..models import Ticket


# --------------------------------------------------------------------
# FIELD MAP — maps your real ServiceNow columns to Ticket model fields
# --------------------------------------------------------------------

FIELD_MAP = {
    "number": ["Number", "number", "inc_number"],
    "short_description": ["Short description", "short_description", "inc_short_description"],
    "description": ["Description", "description", "inc_description"],
    "work_notes": ["Work notes", "work_notes"],   # may not exist — OK
    "resolution_notes": ["Close notes", "resolution_notes"],  # may not exist
    "category": ["Category", "category", "inc_cmdb_ci.category"],
    "subcategory": ["Subcategory", "subcategory", "inc_cmdb_ci.subcategory"],
    "assignment_group": ["Assignment group", "assignment_group", "inc_assignment_group"],
    "ci": ["Configuration item", "ci", "inc_cmdb_ci"],
    "opened_at": ["Opened", "opened_at", "inc_opened_at"],
    "closed_at": ["Closed", "closed_at", "inc_resolved_at"],
}


def get_value(row, keys):
    """Return the first matching key in the CSV row."""
    for k in keys:
        if k in row and row[k]:
            return row[k]
    return ""


# --------------------------------------------------------------------
# DATE PARSER
# --------------------------------------------------------------------

def parse_date(val):
    """Parses ServiceNow-style datetime strings."""
    if not val:
        return None

    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%m/%d/%Y %H:%M", "%m/%d/%Y"):
        try:
            return datetime.strptime(val, fmt)
        except Exception:
            continue

    return None


# --------------------------------------------------------------------
# MAIN CSV IMPORT
# --------------------------------------------------------------------

def import_snow_csv(file_storage):
    """
    Robust CSV loader for ServiceNow exports, handles:
      - cp1252 encoding
      - large files
      - missing columns
      - mixed field naming
    """
    raw_bytes = file_storage.read()
    text = raw_bytes.decode("cp1252", errors="ignore")

    reader = csv.DictReader(io.StringIO(text))
    count = 0

    for row in reader:
        try:
            ticket = Ticket(
                number=get_value(row, FIELD_MAP["number"]),
                short_description=get_value(row, FIELD_MAP["short_description"]),
                description=get_value(row, FIELD_MAP["description"]),
                work_notes=get_value(row, FIELD_MAP["work_notes"]),
                resolution_notes=get_value(row, FIELD_MAP["resolution_notes"]),
                category=get_value(row, FIELD_MAP["category"]),
                subcategory=get_value(row, FIELD_MAP["subcategory"]),
                assignment_group=get_value(row, FIELD_MAP["assignment_group"]),
                ci=get_value(row, FIELD_MAP["ci"]),
                opened_at=parse_date(get_value(row, FIELD_MAP["opened_at"])),
                closed_at=parse_date(get_value(row, FIELD_MAP["closed_at"])),
            )

            db.session.add(ticket)
            count += 1

        except Exception as e:
            print("ROW ERROR:", e, row)
            continue

    db.session.commit()
    return count
