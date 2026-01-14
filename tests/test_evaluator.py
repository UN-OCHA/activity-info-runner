from parser.ast import evaluate_expr, Number, BinaryOp, Identifier, Comparison, String, UnaryOp, FunctionCall
from parser.evaluators import DictResolver

def test_evaluate_number():
    resolver = DictResolver({})
    expr = Number(42.0)
    assert evaluate_expr(expr, resolver) == 42.0

def test_evaluate_identifier():
    data = {"foo": {"bar": 10}}
    resolver = DictResolver(data)
    expr = Identifier(["foo", "bar"])
    assert evaluate_expr(expr, resolver) == 10

def test_evaluate_arithmetic():
    resolver = DictResolver({})
    # 2 + 3 * 4 = 14
    expr = BinaryOp(
        left=Number(2.0),
        op="+",
        right=BinaryOp(
            left=Number(3.0),
            op="*",
            right=Number(4.0)
        )
    )
    assert evaluate_expr(expr, resolver) == 14.0

def test_evaluate_comparison_true():
    data = {"status": "active"}
    resolver = DictResolver(data)
    expr = Comparison(
        left=Identifier(["status"]),
        op="==",
        right=String("active")
    )
    assert evaluate_expr(expr, resolver) is True

def test_evaluate_comparison_false():
    data = {"status": "inactive"}
    resolver = DictResolver(data)
    expr = Comparison(
        left=Identifier(["status"]),
        op="==",
        right=String("active")
    )
    assert evaluate_expr(expr, resolver) is False

def test_evaluate_complex_expression():
    # quantity * price
    data = {"item": {"quantity": 5, "price": 10.5}}
    resolver = DictResolver(data)
    expr = BinaryOp(
        left=Identifier(["item", "quantity"]),
        op="*",
        right=Identifier(["item", "price"])
    )
    assert evaluate_expr(expr, resolver) == 52.5

def test_evaluate_logical_and():
    resolver = DictResolver({})
    # true && false
    expr = BinaryOp(
        left=Comparison(Number(1), "==", Number(1)),
        op="&&",
        right=Comparison(Number(1), "==", Number(2))
    )
    assert evaluate_expr(expr, resolver) is False

    # true && true
    expr2 = BinaryOp(
        left=Comparison(Number(1), "==", Number(1)),
        op="&&",
        right=Comparison(Number(2), "==", Number(2))
    )
    assert evaluate_expr(expr2, resolver) is True

def test_evaluate_logical_or():
    resolver = DictResolver({})
    # true || false
    expr = BinaryOp(
        left=Comparison(Number(1), "==", Number(1)),
        op="||",
        right=Comparison(Number(1), "==", Number(2))
    )
    assert evaluate_expr(expr, resolver) is True

def test_evaluate_not():
    resolver = DictResolver({})
    # !true
    expr = UnaryOp("!", Comparison(Number(1), "==", Number(1)))
    assert evaluate_expr(expr, resolver) is False

def test_evaluate_if():
    resolver = DictResolver({})
    # IF(1 < 2, 10, 20)
    expr = FunctionCall("IF", [
        Comparison(Number(1), "<", Number(2)),
        Number(10),
        Number(20)
    ])
    assert evaluate_expr(expr, resolver) == 10

    # IF(1 > 2, 10, 20)
    expr2 = FunctionCall("IF", [
        Comparison(Number(1), ">", Number(2)),
        Number(10),
        Number(20)
    ])
    assert evaluate_expr(expr2, resolver) == 20

def test_evaluate_isnumber():
    resolver = DictResolver({"val": 123, "text": "abc"})
    
    # ISNUMBER(val) -> True
    expr = FunctionCall("ISNUMBER", [Identifier(["val"])])
    assert evaluate_expr(expr, resolver) is True

    # ISNUMBER(text) -> False
    expr2 = FunctionCall("ISNUMBER", [Identifier(["text"])])
    assert evaluate_expr(expr2, resolver) is False

def test_evaluate_isblank():
    resolver = DictResolver({"val": None, "empty": "", "full": "abc"})
    
    # ISBLANK(val) -> True
    expr = FunctionCall("ISBLANK", [Identifier(["val"])])
    assert evaluate_expr(expr, resolver) is True

    # ISBLANK(empty) -> True
    expr2 = FunctionCall("ISBLANK", [Identifier(["empty"])])
    assert evaluate_expr(expr2, resolver) is True

    # ISBLANK(full) -> False
    expr3 = FunctionCall("ISBLANK", [Identifier(["full"])])
    assert evaluate_expr(expr3, resolver) is False

def test_evaluate_subtraction():
    resolver = DictResolver({})
    expr = BinaryOp(Number(10), "-", Number(4))
    assert evaluate_expr(expr, resolver) == 6.0

def test_evaluate_division():
    resolver = DictResolver({})
    expr = BinaryOp(Number(10), "/", Number(2))
    assert evaluate_expr(expr, resolver) == 5.0

def test_evaluate_coalesce():
    resolver = DictResolver({"a": None, "b": "", "c": "found"})
    # COALESCE(a, b, c) -> "found"
    expr = FunctionCall("COALESCE", [
        Identifier(["a"]),
        Identifier(["b"]),
        Identifier(["c"])
    ])
    assert evaluate_expr(expr, resolver) == "found"

    # COALESCE(a) -> None
    expr2 = FunctionCall("COALESCE", [Identifier(["a"])])
    assert evaluate_expr(expr2, resolver) is None

def test_evaluate_power():
    resolver = DictResolver({})
    expr = FunctionCall("POWER", [Number(2), Number(3)])
    assert evaluate_expr(expr, resolver) == 8.0

def test_evaluate_ceil():
    resolver = DictResolver({})
    expr = FunctionCall("CEIL", [Number(1.1)])
    assert evaluate_expr(expr, resolver) == 2

def test_evaluate_floor():
    resolver = DictResolver({})
    expr = FunctionCall("FLOOR", [Number(1.9)])
    assert evaluate_expr(expr, resolver) == 1

def test_evaluate_round():
    resolver = DictResolver({})
    # ROUND(1.5) -> 2
    expr = FunctionCall("ROUND", [Number(1.5)])
    assert evaluate_expr(expr, resolver) == 2

    # ROUND(1.234, 2) -> 1.23
    expr2 = FunctionCall("ROUND", [Number(1.234), Number(2)])
    assert evaluate_expr(expr2, resolver) == 1.23

def test_evaluate_aggregate_functions():
    resolver = DictResolver({})
    # SUM(1, 2, 3) -> 6
    expr = FunctionCall("SUM", [Number(1), Number(2), Number(3)])
    assert evaluate_expr(expr, resolver) == 6

    # ANY(0, 1) -> True
    expr2 = FunctionCall("ANY", [Number(0), Number(1)])
    assert evaluate_expr(expr2, resolver) is True

    # AVERAGE(2, 4) -> 3
    expr3 = FunctionCall("AVERAGE", [Number(2), Number(4)])
    assert evaluate_expr(expr3, resolver) == 3

    # MAX(1, 5, 2) -> 5
    expr4 = FunctionCall("MAX", [Number(1), Number(5), Number(2)])
    assert evaluate_expr(expr4, resolver) == 5

    # MIN(1, 5, 2) -> 1
    expr5 = FunctionCall("MIN", [Number(1), Number(5), Number(2)])
    assert evaluate_expr(expr5, resolver) == 1

    # COUNT("a", "", "b", None) -> 2
    expr6 = FunctionCall("COUNT", [String("a"), String(""), String("b"), String("")]) 
    # NOTE: ISBLANK considers "" as blank. COUNT should count non-blank.
    # My implementation: arg is not None and arg != ""
    assert evaluate_expr(expr6, resolver) == 2

    # COUNTDISTINCT("a", "b", "a") -> 2
    expr7 = FunctionCall("COUNTDISTINCT", [String("a"), String("b"), String("a")])
    assert evaluate_expr(expr7, resolver) == 2

def test_evaluate_string_functions():
    resolver = DictResolver({})
    
    # TEXT(123) -> "123.0" (float)
    expr = FunctionCall("TEXT", [Number(123.0)])
    assert evaluate_expr(expr, resolver) == "123.0"

    # VALUE("123") -> 123.0
    expr2 = FunctionCall("VALUE", [String("123")])
    assert evaluate_expr(expr2, resolver) == 123.0

    # LOWER("ABC") -> "abc"
    expr3 = FunctionCall("LOWER", [String("ABC")])
    assert evaluate_expr(expr3, resolver) == "abc"

    # TRIM("  abc  ") -> "abc"
    expr4 = FunctionCall("TRIM", [String("  abc  ")])
    assert evaluate_expr(expr4, resolver) == "abc"

    # CONCAT("a", "b") -> "ab"
    expr5 = FunctionCall("CONCAT", [String("a"), String("b")])
    assert evaluate_expr(expr5, resolver) == "ab"

    # LEFT("abc", 1) -> "a"
    expr6 = FunctionCall("LEFT", [String("abc"), Number(1)])
    assert evaluate_expr(expr6, resolver) == "a"

    # RIGHT("abc", 1) -> "c"
    expr7 = FunctionCall("RIGHT", [String("abc"), Number(1)])
    assert evaluate_expr(expr7, resolver) == "c"

    # MID("abc", 2, 1) -> "b"
    expr8 = FunctionCall("MID", [String("abc"), Number(2), Number(1)])
    assert evaluate_expr(expr8, resolver) == "b"

def test_evaluate_search():
    resolver = DictResolver({})
    # SEARCH("b", "abc") -> 2
    expr = FunctionCall("SEARCH", [String("b"), String("abc")])
    assert evaluate_expr(expr, resolver) == 2
    
    # SEARCH("b", "abc", 3) -> None (not found starting at 3)
    expr2 = FunctionCall("SEARCH", [String("b"), String("abc"), Number(3)])
    assert evaluate_expr(expr2, resolver) is None

def test_evaluate_regex_functions():
    resolver = DictResolver({})
    
    # REGEXMATCH("abc", "^a") -> True
    expr = FunctionCall("REGEXMATCH", [String("abc"), String("^a")])
    assert evaluate_expr(expr, resolver) is True

    # REGEXEXTRACT("abc123def", "\\d+") -> "123"
    expr2 = FunctionCall("REGEXEXTRACT", [String("abc123def"), String("\\d+")])
    assert evaluate_expr(expr2, resolver) == "123"

    # REGEXREPLACE("abc", "a", "z") -> "zbc"
    expr3 = FunctionCall("REGEXREPLACE", [String("abc"), String("a"), String("z")])
    assert evaluate_expr(expr3, resolver) == "zbc"

def test_evaluate_edge_cases():
    resolver = DictResolver({})

    # MAX() -> None
    expr = FunctionCall("MAX", [])
    assert evaluate_expr(expr, resolver) is None

    # MIN() -> None
    expr2 = FunctionCall("MIN", [])
    assert evaluate_expr(expr2, resolver) is None
    
    # MAX(1, "a") -> None (TypeError handled)
    expr3 = FunctionCall("MAX", [Number(1), String("a")])
    assert evaluate_expr(expr3, resolver) is None

    # AVERAGE("a", "b") -> 0
    expr4 = FunctionCall("AVERAGE", [String("a"), String("b")])
    assert evaluate_expr(expr4, resolver) == 0

    # VALUE("abc") -> None
    expr5 = FunctionCall("VALUE", [String("abc")])
    assert evaluate_expr(expr5, resolver) is None
    
    # REGEXEXTRACT("abc", "\\d+") -> None
    expr6 = FunctionCall("REGEXEXTRACT", [String("abc"), String("\\d+")])
    assert evaluate_expr(expr6, resolver) is None

    # MID("abc", 0, 1) -> "a" (start < 1 clamped to 1)
    expr7 = FunctionCall("MID", [String("abc"), Number(0), Number(1)])
    assert evaluate_expr(expr7, resolver) == "a"