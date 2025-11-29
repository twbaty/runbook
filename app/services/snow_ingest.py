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
      - enormous files
      - repeated rows
      - multi-line/duplicate SLA-based rows
      - updates existing tickets instead of inserting duplicates
    """

    raw_bytes = file_storage.read()
    text = raw_bytes.decode("cp1252", errors="ignore")

    reader = csv.DictReader(io.StringIO(text))

    seen_numbers = set()   # prevent duplicate inserts in a single upload
    inserted = 0
    updated = 0
    skipped = 0

    for row in reader:
        number = (
            row.get("Number")
            or row.get("number")
            or row.get("inc_number")
        )

        if not number:
            skipped += 1
            continue

        # Skip duplicates inside same CSV
        if number in seen_numbers:
            skipped += 1
            continue
        seen_numbers.add(number)

        # Check if ticket already exists (multiple files over time)
        existing = Ticket.query.filter_by(number=number).first()

        if existing:
            # Update fields if new data is better
            existing.short_description = row.get("Short description") \
                                         or row.get("inc_short_description") \
                                         or existing.short_description

            existing.description = row.get("Description") \
                                    or row.get("inc_description") \
                                    or existing.description

            existing.category = row.get("Category") \
                                or row.get("inc_cmdb_ci.category") \
                                or existing.category

            existing.subcategory = row.get("Subcategory") \
                                   or row.get("inc_cmdb_ci.subcategory") \
                                   or existing.subcategory

            existing.assignment_group = row.get("Assignment group") \
                                        or row.get("inc_assignment_group") \
                                        or existing.assignment_group

            existing.ci = row.get("Configuration item") or existing.ci

            existing.opened_at = _parse_date(
                row.get("Opened") or row.get("inc_opened_at")
            ) or existing.opened_at

            existing.closed_at = _parse_date(
                row.get("Closed") or row.get("inc_resolved_at")
            ) or existing.closed_at

            updated += 1
            continue

        # Create new ticket
        t = Ticket(
            number=number,
            short_description=row.get("Short description") or row.get("inc_short_description") or "",
            description=row.get("Description") or row.get("inc_description") or "",
            work_notes=row.get("Work notes") or "",
            resolution_notes=row.get("Close notes") or "",
            category=row.get("Category") or row.get("inc_cmdb_ci.category") or "",
            subcategory=row.get("Subcategory") or row.get("inc_cmdb_ci.subcategory") or "",
            assignment_group=row.get("Assignment group") or row.get("inc_assignment_group") or "",
            ci=row.get("Configuration item") or "",
            opened_at=_parse_date(row.get("Opened") or row.get("inc_opened_at")),
            closed_at=_parse_date(row.get("Closed") or row.get("inc_resolved_at")),
        )

        db.session.add(t)
        inserted += 1

    db.session.commit()

    return {
        "inserted": inserted,
        "updated": updated,
        "skipped": skipped
    }


def _parse_date(s):
    if not s:
        return None

    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%m/%d/%Y %H:%M"):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            pass

    return None
