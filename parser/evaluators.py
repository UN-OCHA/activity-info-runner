from typing import Dict, Any
from .ast import Identifier

class DictResolver:
    def __init__(self, data: Dict[str, Any]):
        self._data = data

    def resolve(self, identifier: Identifier) -> Any:
        value = self._data
        for part in identifier.parts:
            value = value[part]
        return value