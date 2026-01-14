from .parser import parse_expression
from .ast import Comparison, IdentifierResolver

class ActivityInfoExpression:
    def __init__(self, expr: Comparison):
        self._expr = expr

    @classmethod
    def parse(cls, text: str) -> "ActivityInfoExpression":
        return cls(parse_expression(text))

    def evaluate(self, resolver: IdentifierResolver) -> bool:
        return self._expr.evaluate(resolver)

    @property
    def identifiers(self) -> set[str]:
        return {".".join(self._expr.left.parts)}

    def __str__(self) -> str:
        return self._expr.to_string()

    def debug(self) -> str:
        return repr(self._expr)
