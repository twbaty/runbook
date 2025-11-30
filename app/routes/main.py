# app/routes/main.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from ..extensions import db
from ..models import Ticket, Runbook
from ..services.snow_ingest import import_snow_csv
from ..services.runbook_gen import assign_topics_to_tickets, generate_runbook_for_topic

main_bp = Blueprint("main", __name__)

@main_bp.route("/")
def index():
    topics = (
        db.session.query(Ticket.topic, db.func.count(Ticket.id))
        .filter(Ticket.topic.isnot(None))
        .group_by(Ticket.topic)
        .all()
    )

    runbooks = Runbook.query.order_by(Runbook.last_updated.desc()).all()
    return render_template("index.html", topics=topics, runbooks=runbooks)


@main_bp.route("/upload_snow", methods=["GET", "POST"])
def upload_snow():
    if request.method == "POST":
        file = request.files.get("file")
        if not file:
            flash("No file uploaded", "danger")
            return redirect(request.url)

        # Import SNOW CSV → returns a dict
        result = import_snow_csv(file)

        # Number of NEW tickets inserted
        count = result["inserted"]

        flash(
            f"Imported {result['inserted']} new tickets "
            f"({result['updated']} updated, {result['skipped']} skipped).",
            "success"
        )

        # Pull the newly added tickets
        tickets = (
            Ticket.query
            .order_by(Ticket.id.desc())
            .limit(count)
            .all()
        )

        # Assign topics to only those new tickets
        assign_topics_to_tickets(tickets)

        return redirect(url_for("main.index"))

    return render_template("upload_snow.html")


@main_bp.route("/topic/<topic>")
def view_topic(topic):
    tickets = (
        Ticket.query
        .filter_by(topic=topic)
        .order_by(Ticket.opened_at.desc())
        .all()
    )
    runbook = Runbook.query.filter_by(topic=topic).first()

    return render_template(
        "tickets_by_topic.html",
        topic=topic,
        tickets=tickets,
        runbook=runbook
    )


@main_bp.route("/topic/<topic>/generate", methods=["POST"])
def generate_runbook(topic):
    rb = generate_runbook_for_topic(topic)
    flash(f"Runbook for topic '{topic}' generated/updated.", "success")
    return redirect(url_for("main.view_runbook", runbook_id=rb.id))


@main_bp.route("/runbook/<int:runbook_id>")
def view_runbook(runbook_id):
    rb = Runbook.query.get_or_404(runbook_id)
    return render_template("runbook_view.html", runbook=rb)
