from typing import Dict, Any, List
from .ast import Identifier

class DictResolver:
    """Resolves identifiers against a nested dictionary."""
    def __init__(self, data: Dict[str, Any], originating_data: Dict[str, Any] = None):
        self._data = data
        self._originating_data = originating_data if originating_data is not None else data

    async def resolve(self, identifier: Identifier) -> Any:
        source = self._originating_data if identifier.originating else self._data
        value = source
        for part in identifier.parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return None
        return value

    async def lookup(self, form_id: str, criteria: Any, expression: Any) -> Any:
        raise NotImplementedError("LOOKUP not supported by DictResolver")

    async def aggregate(self, function: str, form_id: str, criteria: Any, expression: Any) -> Any:
        raise NotImplementedError("AGGREGATE not supported by DictResolver")

class RecordResolver(DictResolver):
    def __init__(self, client: Any, data: Dict[str, Any], originating_data: Dict[str, Any] = None):
        super().__init__(data, originating_data)
        self._client = client

    async def lookup(self, form_id: str, criteria: Any, expression: Any) -> Any:
        from .ast import evaluate_expr
        from utils import build_nested_dict
        records = await self._client.api.get_form(form_id)
        for record in records:
            nested_record = build_nested_dict(record)
            record_resolver = RecordResolver(self._client, nested_record, self._originating_data)
            if await evaluate_expr(criteria, record_resolver):
                return await evaluate_expr(expression, record_resolver)
        return None

    async def aggregate(self, function: str, form_id: str, criteria: Any, expression: Any) -> Any:
        from .ast import evaluate_expr
        from utils import build_nested_dict
        records = await self._client.api.get_form(form_id)
        values = []
        for record in records:
            nested_record = build_nested_dict(record)
            record_resolver = RecordResolver(self._client, nested_record, self._originating_data)
            if await evaluate_expr(criteria, record_resolver):
                val = await evaluate_expr(expression, record_resolver)
                if val is not None:
                    values.append(val)
        
        func = function.upper()
        if func == "SUM":
            return sum(v for v in values if isinstance(v, (int, float)))
        if func == "COUNT":
            return len(values)
        if func == "AVERAGE":
            nums = [v for v in values if isinstance(v, (int, float))]
            return sum(nums) / len(nums) if nums else 0
        if func == "MAX":
            return max(values) if values else None
        if func == "MIN":
            return min(values) if values else None
        
        raise ValueError(f"Unknown aggregation function: {func}")