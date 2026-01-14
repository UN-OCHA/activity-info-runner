from parser.parser import parse_expression
from parser.ast import Number, BinaryOp, Identifier, Comparison, UnaryOp, FunctionCall, String

def test_parse_number():
    ast = parse_expression("42")
    assert ast == Number(42.0)

def test_parse_sum():
    ast = parse_expression("1 + 2")
    assert isinstance(ast, BinaryOp)
    assert ast.op == "+"
    assert ast.left == Number(1.0)
    assert ast.right == Number(2.0)

def test_parse_product():
    ast = parse_expression("3 * 4")
    assert isinstance(ast, BinaryOp)
    assert ast.op == "*"
    assert ast.left == Number(3.0)
    assert ast.right == Number(4.0)

def test_precedence():
    # 1 + 2 * 3 should be 1 + (2 * 3)
    ast = parse_expression("1 + 2 * 3")
    assert isinstance(ast, BinaryOp)
    assert ast.op == "+"
    assert ast.left == Number(1.0)
    
    right = ast.right
    assert isinstance(right, BinaryOp)
    assert right.op == "*"
    assert right.left == Number(2.0)
    assert right.right == Number(3.0)

def test_parentheses():
    # (1 + 2) * 3
    ast = parse_expression("(1 + 2) * 3")
    assert isinstance(ast, BinaryOp)
    assert ast.op == "*"
    
    left = ast.left
    assert isinstance(left, BinaryOp)
    assert left.op == "+"
    assert left.left == Number(1.0)
    assert left.right == Number(2.0)
    
    assert ast.right == Number(3.0)

def test_identifier():
    ast = parse_expression("foo.bar")
    assert isinstance(ast, Identifier)
    assert ast.parts == ["foo", "bar"]

def test_comparison():
    ast = parse_expression("user.name == \"Alice\"")
    assert isinstance(ast, Comparison)
    assert isinstance(ast.left, Identifier)
    assert ast.left.parts == ["user", "name"]
    assert ast.op == "=="
    assert isinstance(ast.right, String)
    assert ast.right.value == "Alice"

def test_logical_and():
    ast = parse_expression("a && b")
    assert isinstance(ast, BinaryOp)
    assert ast.op == "&&"

def test_logical_or():
    ast = parse_expression("a || b")
    assert isinstance(ast, BinaryOp)
    assert ast.op == "||"

def test_not():
    ast = parse_expression("!a")
    assert isinstance(ast, UnaryOp)
    assert ast.op == "!"

def test_comparison_ops():
    ops = [">", "<", ">=", "<=", "!="]
    for op in ops:
        ast = parse_expression(f"1 {op} 2")
        assert isinstance(ast, Comparison)
        assert ast.op == op

def test_function_call_if():
    ast = parse_expression("IF(a > 5, 1, 0)")
    assert isinstance(ast, FunctionCall)
    assert ast.name == "IF"
    assert len(ast.args) == 3
    assert isinstance(ast.args[0], Comparison)
    assert isinstance(ast.args[1], Number)
    assert isinstance(ast.args[2], Number)

def test_function_call_isnumber():
    ast = parse_expression("ISNUMBER(val)")
    assert isinstance(ast, FunctionCall)
    assert ast.name == "ISNUMBER"
    assert len(ast.args) == 1

def test_function_call_isblank():
    ast = parse_expression("ISBLANK(val)")
    assert isinstance(ast, FunctionCall)
    assert ast.name == "ISBLANK"
    assert len(ast.args) == 1

def test_subtraction():
    ast = parse_expression("1 - 2")
    assert isinstance(ast, BinaryOp)
    assert ast.op == "-"
    assert ast.left == Number(1.0)
    assert ast.right == Number(2.0)

def test_division():
    ast = parse_expression("10 / 2")
    assert isinstance(ast, BinaryOp)
    assert ast.op == "/"
    assert ast.left == Number(10.0)
    assert ast.right == Number(2.0)

def test_function_coalesce():
    ast = parse_expression("COALESCE(a, b, \"default\")")
    assert isinstance(ast, FunctionCall)
    assert ast.name == "COALESCE"
    assert len(ast.args) == 3

def test_function_power():
    ast = parse_expression("POWER(2, 3)")
    assert isinstance(ast, FunctionCall)
    assert ast.name == "POWER"
    assert len(ast.args) == 2

def test_function_ceil():
    ast = parse_expression("CEIL(1.2)")
    assert isinstance(ast, FunctionCall)
    assert ast.name == "CEIL"
    assert len(ast.args) == 1

def test_function_floor():
    ast = parse_expression("FLOOR(1.9)")
    assert isinstance(ast, FunctionCall)
    assert ast.name == "FLOOR"
    assert len(ast.args) == 1

def test_function_round():
    ast = parse_expression("ROUND(1.234, 2)")
    assert isinstance(ast, FunctionCall)
    assert ast.name == "ROUND"
    assert len(ast.args) == 2