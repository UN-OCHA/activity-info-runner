from lark import Lark, Transformer
from .grammar import GRAMMAR
from .ast import Identifier, Comparison, Number, BinaryOp

_parser = Lark(GRAMMAR, parser="lalr")


class _Transformer(Transformer):
    def dotted_name(self, items):
        return Identifier([str(i) for i in items])

    def NUMBER(self, n):
        return Number(float(n))

    def STRING(self, s):
        return s[1:-1]

    def OP(self, op):
        return str(op)

    def comparison(self, items):
        left, op, right = items
        return Comparison(left, op, right)

    def sum(self, items):
        left, right = items
        return BinaryOp(left, "+", right)

    def product(self, items):
        left, right = items
        return BinaryOp(left, "*", right)


def parse_expression(text: str):
    tree = _parser.parse(text)
    return _Transformer().transform(tree)