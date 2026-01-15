from typing import Any, Set
from .parser import parse_expression
from .ast import Expr, IdentifierResolver, evaluate_expr

class ActivityInfoExpression:
    """Represents an ActivityInfo expression that can be parsed and evaluated."""
    def __init__(self, expr: Expr):
        self._expr = expr

    @classmethod
    def parse(cls, text: str) -> "ActivityInfoExpression":
        return cls(parse_expression(text))

    async def evaluate(self, resolver: IdentifierResolver) -> Any:
        return await evaluate_expr(self._expr, resolver)

    @property
    def identifiers(self) -> Set[str]:
        return self._expr.identifiers()

    def __str__(self) -> str:
        return self._expr.to_string()

    def debug(self) -> str:
        return repr(self._expr)
