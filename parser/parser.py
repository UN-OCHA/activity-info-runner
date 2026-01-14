from lark import Lark, Transformer, v_args
from .grammar import GRAMMAR
from .ast import Identifier, Comparison, Number, BinaryOp, UnaryOp, FunctionCall, String

_parser = Lark(GRAMMAR, parser="lalr")


class _Transformer(Transformer):
    def dotted_name(self, items):
        return Identifier([str(i) for i in items])

    def NUMBER(self, n):
        return Number(float(n))

    def STRING(self, s):
        return String(s[1:-1])

    def or_op(self, items):
        left, right = items
        return BinaryOp(left, "||", right)

    def and_op(self, items):
        left, right = items
        return BinaryOp(left, "&&", right)

    def comparison_op(self, items):
        left, op, right = items
        return Comparison(left, str(op), right)

    def add_op(self, items):
        left, right = items
        return BinaryOp(left, "+", right)

    def sub_op(self, items):
        left, right = items
        return BinaryOp(left, "-", right)

    def mul_op(self, items):
        left, right = items
        return BinaryOp(left, "*", right)

    def div_op(self, items):
        left, right = items
        return BinaryOp(left, "/", right)

    def not_op(self, items):
        (operand,) = items
        return UnaryOp("!", operand)

    def function_call(self, items):
        name = str(items[0])
        args = items[1:] if len(items) > 1 else []
        return FunctionCall(name, args)


def parse_expression(text: str):
    tree = _parser.parse(text)
    return _Transformer().transform(tree)
