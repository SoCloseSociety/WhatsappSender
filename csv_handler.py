"""
WhatsApp Bulk Sender — CSV Contact Importer
Parses CSV files and normalizes phone numbers for WhatsApp sending.
Supports Shopify exports, Google Contacts, and generic CSV formats.
"""

from __future__ import annotations

import io
import logging

import pandas as pd
import phonenumbers

logger = logging.getLogger(__name__)

# Maps common CSV column names to our internal fields
COLUMN_MAP = {
    "phone": "phone",
    "telephone": "phone",
    "tel": "phone",
    "mobile": "phone",
    "numero": "phone",
    "billing phone": "phone",
    "shipping phone": "phone",
    "address_phone": "phone",
    "first_name": "first_name",
    "first name": "first_name",
    "firstname": "first_name",
    "prenom": "first_name",
    "billing first name": "first_name",
    "last_name": "last_name",
    "last name": "last_name",
    "lastname": "last_name",
    "nom": "last_name",
    "billing last name": "last_name",
    "name": "name",
    "full_name": "name",
    "fullname": "name",
    "email": "email",
    "e-mail": "email",
    "billing email": "email",
}


def normalize_phone(raw_phone: str, default_region: str = "FR") -> str | None:
    """
    Normalize a phone number to E.164 format (+33612345678).
    Returns None if the number is invalid.
    """
    if not raw_phone or not raw_phone.strip():
        return None

    raw = raw_phone.strip()

    try:
        parsed = phonenumbers.parse(raw, default_region)
        if phonenumbers.is_valid_number(parsed):
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except phonenumbers.NumberParseException:
        pass

    # Fallback: if it looks like a number with enough digits
    digits = "".join(c for c in raw if c.isdigit())
    if len(digits) >= 8:
        return f"+{digits}"

    return None


def parse_csv(file_content: bytes | str) -> tuple[list[dict], list[str]]:
    """
    Parse a CSV file and extract contacts.

    Args:
        file_content: Raw CSV content (bytes or string)

    Returns:
        (valid_contacts, errors) where valid_contacts is a list of
        {"first_name": ..., "last_name": ..., "phone": ..., "email": ...}
    """
    # Handle encoding
    if isinstance(file_content, bytes):
        for encoding in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                text = file_content.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            return [], ["Impossible de decoder le fichier CSV."]
    else:
        text = file_content

    # Parse with pandas
    try:
        df = pd.read_csv(io.StringIO(text), dtype=str, keep_default_na=False)
    except Exception as e:
        return [], [f"Erreur de parsing CSV: {e}"]

    if df.empty:
        return [], ["Le fichier CSV est vide."]

    # Map columns
    col_map = {}
    for col in df.columns:
        normalized = col.strip().lower()
        if normalized in COLUMN_MAP:
            internal = COLUMN_MAP[normalized]
            if internal not in col_map:
                col_map[internal] = col

    if "phone" not in col_map:
        return [], [f"Aucune colonne 'phone' trouvee. Colonnes disponibles: {', '.join(df.columns)}"]

    # Extract contacts
    contacts = []
    errors = []
    seen_phones = set()

    for idx, row in df.iterrows():
        line_num = idx + 2  # +2 for header + 0-index

        raw_phone = str(row.get(col_map["phone"], "")).strip()
        phone = normalize_phone(raw_phone)

        if not phone:
            errors.append(f"Ligne {line_num}: numero invalide '{raw_phone}'")
            continue

        if phone in seen_phones:
            continue
        seen_phones.add(phone)

        # Extract name fields
        first_name = ""
        last_name = ""

        if "first_name" in col_map:
            first_name = str(row.get(col_map["first_name"], "")).strip()
        if "last_name" in col_map:
            last_name = str(row.get(col_map["last_name"], "")).strip()

        # If we have a single "name" column, split it
        if not first_name and "name" in col_map:
            full_name = str(row.get(col_map["name"], "")).strip()
            parts = full_name.split(None, 1)
            first_name = parts[0] if parts else ""
            last_name = parts[1] if len(parts) > 1 else ""

        email = ""
        if "email" in col_map:
            email = str(row.get(col_map["email"], "")).strip()

        contacts.append({
            "first_name": first_name or "Contact",
            "last_name": last_name,
            "phone": phone,
            "email": email,
        })

    return contacts, errors
