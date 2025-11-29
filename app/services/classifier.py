# app/services/classifier.py
import re


# ----------------------------------------------------
#  BASE TAXONOMY
#  (built from your actual SNOW sample data)
# ----------------------------------------------------
TAXONOMY = {
    "email_issue": [
        r"email",
        r"outlook",
        r"mailbox",
        r"ndr",
        r"not receiving",
        r"unable to send",
        r"delivery failure",
        r"smtp",
        r"shared mailbox",
        r"distribution list",
    ],

    "access_issue": [
        r"password",
        r"unlock",
        r"account",
        r"login",
        r"credential",
        r"mfa",
        r"duo",
        r"permission",
        r"unauthorized",
        r"sso",
        r"access request",
        r"group membership",
    ],

    "endpoint_issue": [
        r"computer",
        r"workstation",
        r"device",
        r"desktop",
        r"laptop",
        r"blue screen",
        r"disk",
        r"antivirus",
        r"slow",
        r"won'?t boot",
        r"crash",
    ],

    "network_issue": [
        r"vpn",
        r"network",
        r"wifi",
        r"no connectivity",
        r"port",
    ],

    "application_issue": [
        r"epic",
        r"citrix",
        r"kronos",
        r"teams",
        r"onedrive",
        r"sharepoint",
        r"printer",
        r"fax",
        r"snow",
        r"servicenow",
    ],
}


# ----------------------------------------------------
#  NORMALIZER
# ----------------------------------------------------
def _norm(text):
    if not text:
        return ""
    return text.lower().strip()


# ----------------------------------------------------
#  RULE-BASED CLASSIFIER
# ----------------------------------------------------
def classify_ticket(ticket):
    """
    Deterministic classifier built from your real SNOW ticket language.
    No LLM unless everything fails.
    """

    text = " ".join([
        _norm(ticket.short_description),
        _norm(ticket.description),
        _norm(ticket.category),
        _norm(ticket.subcategory),
        _norm(ticket.assignment_group),
        _norm(ticket.ci),
    ])

    if not text.strip():
        return "other"

    # Pattern match by topic
    for topic, patterns in TAXONOMY.items():
        for p in patterns:
            if re.search(p, text):
                return topic

    return "other"
