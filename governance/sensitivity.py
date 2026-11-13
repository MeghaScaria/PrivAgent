"""
Sensitivity labels and how they combine.

A label is {"value": 1 | 0 | None, "basis": why, ...}: 1 sensitive,
0 not sensitive, None unknown. Unknown is never treated as safe: for any
security decision, effective_value() turns None into 1.

Provenance (what data an agent actually received, see
governance/provenance.py) is the authoritative signal. What an agent
declares about its own output is kept alongside for auditing, and can
only make a decision stricter: authoritative_label() takes the higher of
the two, so a declaration of "not sensitive" can never lower a
provenance label of "sensitive" or "unknown".
"""
import re

ASSESSOR_VERSION = "pii-regex-1"

_PATTERNS = {
    "email": re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
    "us_ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "iban": re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b"),
    "bank_account": re.compile(r"\b[A-Z]{4}\d{10,}\b|\b\d{10,18}\b"),
    "phone": re.compile(r"(?<!\d)(?:\+\d{1,3}[ .-]?)?\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}(?!\d)"),
}
_CARD = re.compile(r"\b(?:\d[ -]?){13,19}\b")


def _luhn_ok(digits):
    total, parity = 0, len(digits) % 2
    for i, ch in enumerate(digits):
        d = int(ch)
        if i % 2 == parity:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def assess_text(text, source):
    """Pattern-based check for personal or financial identifiers in free
    text (e.g. the user's task). It can show that something sensitive is
    present, not prove that nothing is, so a clean result is labelled
    'no PII detected' with the assessor version, not 'not sensitive'
    by assumption. Only detector names go in the label, never the
    matched text."""
    if not isinstance(text, str):
        return {"value": None, "basis": f"{source}_not_text", "assessor": ASSESSOR_VERSION}
    found = sorted(name for name, pattern in _PATTERNS.items() if pattern.search(text))
    for match in _CARD.finditer(text):
        digits = re.sub(r"\D", "", match.group())
        if 13 <= len(digits) <= 19 and _luhn_ok(digits):
            found.append("payment_card")
            break
    if found:
        return {"value": 1, "basis": f"{source}_pii_detected", "detectors": found,
                "assessor": ASSESSOR_VERSION}
    return {"value": 0, "basis": f"{source}_no_pii_detected", "assessor": ASSESSOR_VERSION}


def combine(values):
    """Sensitivity of something built from inputs with these values:
    1 if any is sensitive, else unknown if any is unknown, else 0."""
    values = list(values)
    if 1 in values:
        return 1
    if None in values:
        return None
    return 0


def effective_value(value):
    """The value to act on: unknown counts as sensitive."""
    return 1 if value is None else int(value)


def authoritative_label(provenance, declared):
    """provenance: a label from the provenance registry. declared: what
    the acting agent said (0/1, or None if it said nothing).
    Returns the authoritative label plus any mismatch flags."""
    prov_value = provenance["value"]
    effective = effective_value(prov_value)
    flags = []
    if prov_value is None:
        flags.append("provenance_unknown_treated_as_sensitive")
    if declared is not None:
        if int(declared) < effective:
            flags.append("declared_lower_than_provenance")
        elif int(declared) > effective:
            flags.append("declared_higher_than_provenance")
        effective = max(effective, int(declared))
    return {
        "value": effective,
        "basis": "provenance" if "declared_higher_than_provenance" not in flags
                 else "agent_declaration_stricter_than_provenance",
        "provenance": provenance,
        "declared": declared,
    }, flags
