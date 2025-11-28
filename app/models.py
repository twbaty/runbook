# app/models.py
from datetime import datetime
from .extensions import db

class Ticket(db.Model):
    __tablename__ = "tickets"

    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(64), index=True)
    short_description = db.Column(db.Text)
    description = db.Column(db.Text)
    work_notes = db.Column(db.Text)
    resolution_notes = db.Column(db.Text)
    category = db.Column(db.String(128))
    subcategory = db.Column(db.String(128))
    assignment_group = db.Column(db.String(128))
    ci = db.Column(db.String(256))
    opened_at = db.Column(db.DateTime)
    closed_at = db.Column(db.DateTime)

    topic = db.Column(db.String(128), index=True)  # AI-assigned label later

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Runbook(db.Model):
    __tablename__ = "runbooks"

    id = db.Column(db.Integer, primary_key=True)
    topic = db.Column(db.String(128), index=True)
    title = db.Column(db.String(256))
    markdown = db.Column(db.Text)     # rendered final content
    json_blob = db.Column(db.Text)    # optional raw structured JSON
    tickets_used = db.Column(db.Integer)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
