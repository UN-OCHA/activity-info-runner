from __future__ import annotations
from dataclasses import dataclass
from typing import List, Literal, Protocol, Any, Union


class IdentifierResolver(Protocol):
    def resolve(self, identifier: "Identifier") -> Any: ...

# ---------- Expression Evaluation ----------

def evaluate_expr(expr: Expr, resolver: IdentifierResolver) -> float:
    if isinstance(expr, Identifier):
        return resolver.resolve(expr)
    if isinstance(expr, Number):
        return expr.value
    if isinstance(expr, BinaryOp):
        return expr.evaluate(resolver)
    raise TypeError(expr)


# ---------- Core ----------

class ExprNode:
    def to_string(self) -> str:
        return str(self)


@dataclass(frozen=True)
class Identifier(ExprNode):
    parts: List[str]

    def __str__(self) -> str:
        return ".".join(self.parts)

# ---------- Arithmetic ----------

@dataclass(frozen=True)
class Number:
    value: float

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class BinaryOp(ExprNode):
    left: "Expr"
    op: Literal["+", "*"]
    right: "Expr"

    def evaluate(self, resolver: IdentifierResolver) -> float:
        l = evaluate_expr(self.left, resolver)
        r = evaluate_expr(self.right, resolver)

        if self.op == "+":
            return l + r
        if self.op == "*":
            return l * r
        raise ValueError(self.op)

    def __str__(self) -> str:
        return f"({self.left} {self.op} {self.right})"


# ---------- Boolean ----------

@dataclass(frozen=True)
class Comparison(ExprNode):
    left: Identifier
    op: Literal["==", "!="]
    right: str

    def evaluate(self, resolver: IdentifierResolver) -> bool:
        value = resolver.resolve(self.left)
        return value == self.right if self.op == "==" else value != self.right

    def __str__(self) -> str:
        return f'{self.left} {self.op} "{self.right}"'


Expr = Union[Identifier, Number, BinaryOp]