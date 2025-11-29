# app/services/classifier.py
"""
Deterministic, high-speed ticket classifier for SNOW incident imports.

ORDER OF OPERATIONS:
1. Normalize text
2. Apply strict keyword taxonomy (fastest, best quality)
3. Apply fuzzy keyword families (catch mixed wording)
4. If still ambiguous → classify as "other"
5. Optional LLM fallback (disabled by default for performance)

This is tuned for large SNOW datasets (100k–700k lines).
"""

import re
from .phi_scrub import scrub_text

# ============================================================
# TAXONOMY DEFINITIONS (hand-tuned)
# ============================================================

TAXONOMY = {
    "email_issue": [
        r"email", r"mail", r"outlook", r"exchange",
        r"o365", r"office\s*365",
        r"phish", r"spam", r"junk",
        r"undeliver", r"bounce", r"mailer-daemon",
        r"recipient", r"inbox", r"mfa\s*email"
    ],

    "endpoint_issue": [
        r"laptop", r"desktop", r"workstation", r"computer",
        r"blue\s*screen", r"bsod", r"crash", r"freeze",
        r"boot", r"startup", r"no\s*power",
        r"slow", r"performance", r"slowness"
    ],

    "access_issue": [
        r"access", r"permission", r"permissions",
        r"login", r"log in", r"credential", r"username",
        r"password", r"locked\s*out", r"unlock",
        r"account\s*issue"
    ],

    "cloud_issue": [
        r"aws", r"azure", r"gcp", r"cloud",
        r"s3", r"bucket", r"cloudflare",
        r"vm\s*error", r"virtual\s*machine"
    ],

    "security_issue": [
        r"malware", r"virus", r"trojan", r"ransom",
        r"infect", r"compromise", r"security",
        r"threat", r"alert"
    ],
}

# Explicit fast-path overrides (very high signal)
HARDCODED = [
    (r"vpn", "vpn_issue"),
    (r"duo|okta|mfa|2fa", "access_issue"),
]


# ============================================================
# CLASSIFIER
# ============================================================

def classify_ticket(ticket):
    """
    Main entry point used by runbook_gen.py.
    Input: Ticket object
    Output: short deterministic label
    """

    text = f"{ticket.short_description} {ticket.description or ''}".lower()
    text = scrub_text(text)

    # -----------------------------
    # 1. HARD OVERRIDES
    # -----------------------------
    for pattern, label in HARDCODED:
        if re.search(pattern, text):
            return label

    # -----------------------------
    # 2. APPLY TAXONOMY
    # -----------------------------
    best_label = None
    best_hits = 0

    for label, patterns in TAXONOMY.items():
        hits = sum(1 for p in patterns if re.search(p, text))
        if hits > best_hits:
            best_hits = hits
            best_label = label

    # Very strong match → accept
    if best_hits >= 2:
        return best_label

    # Weak signal but at least one match → accept it as low-confidence
    if best_hits == 1:
        return best_label

    # -----------------------------
    # 3. CATCH ALL
    # -----------------------------
    return "other"
