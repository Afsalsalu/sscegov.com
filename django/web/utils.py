import re


def sanitize_input(user_input):
    # Allow only alphanumeric characters, no newlines or control characters
    sanitized = re.sub(r"[^a-zA-Z0-9.-]", "", user_input)
    return sanitized


def dms_to_decimal(degrees, minutes, seconds, direction):
    decimal = float(degrees) + float(minutes) / 60 + float(seconds) / 3600
    if direction in ["S", "W"]:
        decimal = -decimal
    return decimal


def convert_dms(dms_str):
    dms_pattern = re.compile(r"(\d+)°(\d+)'([\d\.]+)\"([NSEW])")
    match = dms_pattern.match(dms_str.strip())
    if match:
        degrees, minutes, seconds, direction = match.groups()
        return dms_to_decimal(degrees, minutes, seconds, direction)
    raise ValueError("Invalid DMS format")
