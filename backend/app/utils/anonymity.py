"""
Pseudo-anonymity and Identifier Masking Utilities for Mentaura Platform.
Safeguards vulnerable victim and witness identities across dashboards and public-facing APIs.
"""
from typing import Optional

def mask_identifier(
    full_name: Optional[str], 
    user_id: Optional[str] = None, 
    include_uuid: bool = False
) -> str:
    """
    Format a masked identifier adhering to the style: "A****a S."
    Optional short UUID suffix: "A****a S. (#3f764a)" for administrative/dashboard tracking.
    """
    if not full_name or not full_name.strip():
        if user_id:
            short_id = str(user_id)[:6]
            return f"User #{short_id}"
        return "Protected Person"

    parts = full_name.strip().split()
    if not parts:
        return "Protected Person"

    first = parts[0]
    if len(first) == 1:
        first_masked = f"{first.upper()}*"
    elif len(first) == 2:
        first_masked = f"{first[0].upper()}*"
    else:
        first_masked = f"{first[0].upper()}****{first[-1].lower()}"

    subsequent = []
    for part in parts[1:]:
        if part:
            subsequent.append(f"{part[0].upper()}.")

    if subsequent:
        name_masked = f"{first_masked} {' '.join(subsequent)}"
    else:
        name_masked = first_masked

    if include_uuid and user_id:
        short_id = str(user_id)[:6]
        return f"{name_masked} (#{short_id})"

    return name_masked

def mask_email(email: Optional[str]) -> str:
    """
    Mask email address (e.g. anita.sharma@example.com -> a****a@example.com).
    """
    if not email or "@" not in email:
        return "p****d@domain.local"
    local_part, domain = email.split("@", 1)
    if len(local_part) <= 2:
        masked_local = f"{local_part[0]}*"
    else:
        masked_local = f"{local_part[0]}****{local_part[-1]}"
    return f"{masked_local}@{domain}"
 
def mask_phone(phone: Optional[str]) -> Optional[str]:
    """
    Mask phone number (e.g. +91 98765 43210 -> +91 98*** **210).
    """
    if not phone or not phone.strip():
        return None
    clean = phone.strip()
    if len(clean) <= 5:
        return "*****"
    return f"{clean[:3]}***{clean[-3:]}"
