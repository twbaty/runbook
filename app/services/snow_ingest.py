# app/services/snow_ingest.py
import csv
import io
from datetime import datetime

from ..extensions import db
from ..models import Ticket


def import_snow_csv(file_storage):
    """
    Loads ServiceNow CSV in your custom schema (inc_* columns).
    """

    raw_bytes = file_storage.read()
    text = raw_bytes.decode("cp1252", errors="ignore")

    reader = csv.DictReader(io.StringIO(text))

    count = 0
    for row in reader:
        try:
            t = Ticket(
                number=row.get("inc_number"),
                short_description=row.get("inc_short_description", ""),
                description=row.get("inc_description", ""),
                work_notes="",                    # Not provided in file
                resolution_notes="",              # Not provided in file
                category=row.get("inc_cmdb_ci.category", ""),
                subcategory=row.get("inc_cmdb_ci.subcategory", ""),
                assignment_group=row.get("inc_assignment_group", ""),
                ci=row.get("inc_cmdb_ci", ""),
                opened_at=_parse_date(row.get("inc_opened_at")),
                closed_at=_parse_date(row.get("inc_resolved_at")),
            )

            db.session.add(t)
            count += 1

        except Exception as e:
            print("ROW ERROR:", e, row)
            continue

    db.session.commit()
    return count


def _parse_date(s):
    if not s:
        return None

    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            pass

    return None
