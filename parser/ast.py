from __future__ import annotations
from dataclasses import dataclass
from typing import List, Literal, Protocol, Any, Union, Set
import math
import re


class IdentifierResolver(Protocol):
    def resolve(self, identifier: "Identifier") -> Any: ...

# ---------- Expression Evaluation ----------

def evaluate_expr(expr: Expr, resolver: IdentifierResolver) -> Any:
    if isinstance(expr, Identifier):
        return resolver.resolve(expr)
    if isinstance(expr, Number):
        return expr.value
    if isinstance(expr, String):
        return expr.value
    if isinstance(expr, BinaryOp):
        return expr.evaluate(resolver)
    if isinstance(expr, Comparison):
        return expr.evaluate(resolver)
    if isinstance(expr, UnaryOp):
        return expr.evaluate(resolver)
    if isinstance(expr, FunctionCall):
        return expr.evaluate(resolver)
    raise TypeError(expr)


# ---------- Core ----------

class ExprNode:
    def to_string(self) -> str:
        return str(self)
    
    def identifiers(self) -> Set[str]:
        return set()


@dataclass(frozen=True)
class Identifier(ExprNode):
    parts: List[str]

    def __str__(self) -> str:
        return ".".join(self.parts)

    def identifiers(self) -> Set[str]:
        return {str(self)}

@dataclass(frozen=True)
class String(ExprNode):
    value: str

    def __str__(self) -> str:
        return f'"{self.value}"'

# ---------- Arithmetic / Logical ----------

@dataclass(frozen=True)
class Number:
    value: float

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class BinaryOp(ExprNode):
    left: "Expr"
    op: str
    right: "Expr"

    def evaluate(self, resolver: IdentifierResolver) -> Any:
        l = evaluate_expr(self.left, resolver)
        
        # Short-circuit logic
        if self.op == "&&":
            return bool(l) and bool(evaluate_expr(self.right, resolver))
        if self.op == "||":
            return bool(l) or bool(evaluate_expr(self.right, resolver))

        r = evaluate_expr(self.right, resolver)

        if self.op == "+":
            return l + r
        if self.op == "*":
            return l * r
        if self.op == "-":
            return l - r
        if self.op == "/":
            return l / r
        
        raise ValueError(f"Unknown operator: {self.op}")

    def __str__(self) -> str:
        return f"({self.left} {self.op} {self.right})"

    def identifiers(self) -> Set[str]:
        return self.left.identifiers() | self.right.identifiers()


@dataclass(frozen=True)
class UnaryOp(ExprNode):
    op: str
    operand: "Expr"

    def evaluate(self, resolver: IdentifierResolver) -> Any:
        val = evaluate_expr(self.operand, resolver)
        if self.op == "!":
            return not val
        raise ValueError(f"Unknown unary operator: {self.op}")

    def __str__(self) -> str:
        return f"{self.op}({self.operand})"

    def identifiers(self) -> Set[str]:
        return self.operand.identifiers()

# ---------- Comparison ----------

@dataclass(frozen=True)
class Comparison(ExprNode):
    left: "Expr"
    op: str
    right: "Expr"

    def evaluate(self, resolver: IdentifierResolver) -> bool:
        l = evaluate_expr(self.left, resolver)
        r = evaluate_expr(self.right, resolver)

        if self.op == "==": return l == r
        if self.op == "!=": return l != r
        if self.op == "<": return l < r
        if self.op == ">": return l > r
        if self.op == "<=": return l <= r
        if self.op == ">=": return l >= r
        
        raise ValueError(f"Unknown comparison operator: {self.op}")

    def __str__(self) -> str:
        return f"({self.left} {self.op} {self.right})"

    def identifiers(self) -> Set[str]:
        return self.left.identifiers() | self.right.identifiers()


# ---------- Functions ----------

@dataclass(frozen=True)
class FunctionCall(ExprNode):
    name: str
    args: List["Expr"]

    def evaluate(self, resolver: IdentifierResolver) -> Any:
        func_name = self.name.upper()
        
        if func_name == "IF":
            if len(self.args) not in (2, 3):
                raise ValueError("IF expects 2 or 3 arguments")
            condition = evaluate_expr(self.args[0], resolver)
            if condition:
                return evaluate_expr(self.args[1], resolver)
            elif len(self.args) == 3:
                return evaluate_expr(self.args[2], resolver)
            return None 

        if func_name == "ISNUMBER":
            if len(self.args) != 1:
                raise ValueError("ISNUMBER expects 1 argument")
            val = evaluate_expr(self.args[0], resolver)
            return isinstance(val, (int, float)) and not isinstance(val, bool)

        if func_name == "ISBLANK":
            if len(self.args) != 1:
                raise ValueError("ISBLANK expects 1 argument")
            val = evaluate_expr(self.args[0], resolver)
            return val is None or val == ""
            
        if func_name == "COALESCE":
            if not self.args:
                raise ValueError("COALESCE expects at least 1 argument")
            for arg in self.args:
                val = evaluate_expr(arg, resolver)
                if val is not None and val != "":
                    return val
            return None

        if func_name == "POWER":
            if len(self.args) != 2:
                raise ValueError("POWER expects 2 arguments")
            base = evaluate_expr(self.args[0], resolver)
            exp = evaluate_expr(self.args[1], resolver)
            return math.pow(base, exp)

        if func_name == "CEIL":
            if len(self.args) != 1:
                raise ValueError("CEIL expects 1 argument")
            val = evaluate_expr(self.args[0], resolver)
            return math.ceil(val)

        if func_name == "FLOOR":
            if len(self.args) != 1:
                raise ValueError("FLOOR expects 1 argument")
            val = evaluate_expr(self.args[0], resolver)
            return math.floor(val)
        
        if func_name == "ROUND":
            if len(self.args) not in (1, 2):
                raise ValueError("ROUND expects 1 or 2 arguments")
            val = evaluate_expr(self.args[0], resolver)
            digits = 0
            if len(self.args) == 2:
                digits = int(evaluate_expr(self.args[1], resolver))
            return round(val, digits)

        evaluated_args = [evaluate_expr(arg, resolver) for arg in self.args]
        
        if func_name == "SUM":
            return sum(arg for arg in evaluated_args if isinstance(arg, (int, float)))

        if func_name == "ANY":
            return any(bool(arg) for arg in evaluated_args)

        if func_name == "AVERAGE":
            nums = [arg for arg in evaluated_args if isinstance(arg, (int, float))]
            if not nums: return 0
            return sum(nums) / len(nums)
        
        if func_name == "MAX":
            if not evaluated_args: return None
            try:
                return max(evaluated_args)
            except TypeError:
                return None

        if func_name == "MIN":
            if not evaluated_args: return None
            try:
                return min(evaluated_args)
            except TypeError:
                return None

        if func_name == "COUNT":
            return len([arg for arg in evaluated_args if arg is not None and arg != ""])

        if func_name == "COUNTDISTINCT":
            return len(set(arg for arg in evaluated_args if arg is not None and arg != ""))
        
        if func_name == "TEXT":
            if len(self.args) != 1: raise ValueError("TEXT expects 1 argument")
            return str(evaluated_args[0])

        if func_name == "VALUE":
            if len(self.args) != 1: raise ValueError("VALUE expects 1 argument")
            try:
                return float(evaluated_args[0])
            except (ValueError, TypeError):
                return None

        if func_name == "LOWER":
            if len(self.args) != 1: raise ValueError("LOWER expects 1 argument")
            return str(evaluated_args[0]).lower()

        if func_name == "TRIM":
            if len(self.args) != 1: raise ValueError("TRIM expects 1 argument")
            return str(evaluated_args[0]).strip()
        
        if func_name == "CONCAT":
            return "".join(str(arg) for arg in evaluated_args)
        
        if func_name == "LEFT":
            if len(self.args) != 2: raise ValueError("LEFT expects 2 arguments")
            text = str(evaluated_args[0])
            n = int(evaluated_args[1])
            return text[:n]

        if func_name == "RIGHT":
            if len(self.args) != 2: raise ValueError("RIGHT expects 2 arguments")
            text = str(evaluated_args[0])
            n = int(evaluated_args[1])
            return text[-n:] if n > 0 else ""

        if func_name == "MID":
            if len(self.args) != 3: raise ValueError("MID expects 3 arguments")
            text = str(evaluated_args[0])
            start = int(evaluated_args[1])
            n = int(evaluated_args[2])
            if start < 1: start = 1
            return text[start-1 : start-1+n]

        if func_name == "SEARCH":
            if len(self.args) not in (2, 3): raise ValueError("SEARCH expects 2 or 3 arguments")
            sub = str(evaluated_args[0])
            text = str(evaluated_args[1])
            start = 1
            if len(self.args) == 3:
                start = int(evaluated_args[2])
            try:
                idx = text.lower().find(sub.lower(), start - 1)
                if idx == -1: return None
                return idx + 1
            except Exception:
                return None
        
        if func_name == "REGEXMATCH":
            if len(self.args) != 2: raise ValueError("REGEXMATCH expects 2 arguments")
            text = str(evaluated_args[0])
            pattern = str(evaluated_args[1])
            return bool(re.search(pattern, text))
        
        if func_name == "REGEXEXTRACT":
            if len(self.args) != 2: raise ValueError("REGEXEXTRACT expects 2 arguments")
            text = str(evaluated_args[0])
            pattern = str(evaluated_args[1])
            match = re.search(pattern, text)
            if match:
                return match.group(0)
            return None

        if func_name == "REGEXREPLACE":
            if len(self.args) != 3: raise ValueError("REGEXREPLACE expects 3 arguments")
            text = str(evaluated_args[0])
            pattern = str(evaluated_args[1])
            replacement = str(evaluated_args[2])
            return re.sub(pattern, replacement, text)

        raise ValueError(f"Unknown function: {func_name}")

    def __str__(self) -> str:
        args_str = ", ".join(str(arg) for arg in self.args)
        return f"{self.name}({args_str})"

    def identifiers(self) -> Set[str]:
        ids = set()
        for arg in self.args:
            ids |= arg.identifiers()
        return ids


Expr = Union[Identifier, Number, String, BinaryOp, UnaryOp, Comparison, FunctionCall]