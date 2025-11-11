import re

def to_float(value, default=0.0):
    """
    Safely convert a value to float. Extracts the first numeric part if text.
    Returns default if no valid number is found.
    """
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        match = re.search(r"\d+(\.\d+)?", value)
        if match:
            return float(match.group())
    return default
