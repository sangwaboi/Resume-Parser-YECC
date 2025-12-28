import re
def clean_array(arr):
    if not arr:
        return []
    cleaned = []
    for item in arr:
        if item and str(item).strip():
            clean_item = str(item).strip()
            if clean_item not in cleaned:
                cleaned.append(clean_item)
    return cleaned
def extract_email(text):
    email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    match = re.search(email_pattern, text)
    return match.group(0) if match else None
def extract_phone(text):
    phone_patterns = [
        r"\+?91[\s-]?\d{10}",
        r"\d{10}",
        r"\d{5}[\s-]?\d{5}",
    ]
    for pattern in phone_patterns:
        match = re.search(pattern, text)
        if match:
            phone = re.sub(r"[^\d]", "", match.group(0))
            if len(phone) >= 10:
                return phone[-10:]
    return None
def extract_linkedin(text):
    linkedin_pattern = r"(?:https?://)?(?:www\.)?linkedin\.com/in/[a-zA-Z0-9_-]+"
    match = re.search(linkedin_pattern, text, re.IGNORECASE)
    return match.group(0) if match else None
def safe_join(items, separator=", "):
    if not items:
        return ""
    return separator.join(str(item) for item in items if item)
