from typing import Dict, Any

def build_nested_dict(flat: Dict[str, Any]) -> Dict:
    """Converts a flat dictionary with dot-separated keys into a nested dictionary."""
    nested: Dict = {}
    for key, value in flat.items():
        parts = key.split(".")
        d = nested
        for part in parts[:-1]:
            if part not in d:
                d[part] = {}
            d = d[part]
        d[parts[-1]] = value
    return nested
