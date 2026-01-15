from parser.ast import evaluate_expr, Number, BinaryOp, Identifier, Comparison, String, UnaryOp, FunctionCall
from parser.evaluators import DictResolver

async def test_evaluate_number():
    resolver = DictResolver({})
    expr = Number(42.0)
    assert await evaluate_expr(expr, resolver) == 42.0

async def test_evaluate_identifier():
    data = {"foo": {"bar": 10}}
    resolver = DictResolver(data)
    expr = Identifier(["foo", "bar"])
    assert await evaluate_expr(expr, resolver) == 10

async def test_evaluate_arithmetic():
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
    assert await evaluate_expr(expr, resolver) == 14.0

async def test_evaluate_comparison_true():
    data = {"status": "active"}
    resolver = DictResolver(data)
    expr = Comparison(
        left=Identifier(["status"]),
        op="==",
        right=String("active")
    )
    assert await evaluate_expr(expr, resolver) is True

async def test_evaluate_comparison_false():
    data = {"status": "inactive"}
    resolver = DictResolver(data)
    expr = Comparison(
        left=Identifier(["status"]),
        op="==",
        right=String("active")
    )
    assert await evaluate_expr(expr, resolver) is False

async def test_evaluate_complex_expression():
    # quantity * price
    data = {"item": {"quantity": 5, "price": 10.5}}
    resolver = DictResolver(data)
    expr = BinaryOp(
        left=Identifier(["item", "quantity"]),
        op="*",
        right=Identifier(["item", "price"])
    )
    assert await evaluate_expr(expr, resolver) == 52.5

async def test_evaluate_logical_and():
    resolver = DictResolver({})
    # true && false
    expr = BinaryOp(
        left=Comparison(Number(1), "==", Number(1)),
        op="&&",
        right=Comparison(Number(1), "==", Number(2))
    )
    assert await evaluate_expr(expr, resolver) is False

    # true && true
    expr2 = BinaryOp(
        left=Comparison(Number(1), "==", Number(1)),
        op="&&",
        right=Comparison(Number(2), "==", Number(2))
    )
    assert await evaluate_expr(expr2, resolver) is True

async def test_evaluate_logical_or():
    resolver = DictResolver({})
    # true || false
    expr = BinaryOp(
        left=Comparison(Number(1), "==", Number(1)),
        op="||",
        right=Comparison(Number(1), "==", Number(2))
    )
    assert await evaluate_expr(expr, resolver) is True

async def test_evaluate_not():
    resolver = DictResolver({})
    # !true
    expr = UnaryOp("!", Comparison(Number(1), "==", Number(1)))
    assert await evaluate_expr(expr, resolver) is False

async def test_evaluate_if():
    resolver = DictResolver({})
    # IF(1 < 2, 10, 20)
    expr = FunctionCall("IF", [
        Comparison(Number(1), "<", Number(2)),
        Number(10),
        Number(20)
    ])
    assert await evaluate_expr(expr, resolver) == 10

    # IF(1 > 2, 10, 20)
    expr2 = FunctionCall("IF", [
        Comparison(Number(1), ">", Number(2)),
        Number(10),
        Number(20)
    ])
    assert await evaluate_expr(expr2, resolver) == 20

async def test_evaluate_isnumber():
    resolver = DictResolver({"val": 123, "text": "abc"})
    
    # ISNUMBER(val) -> True
    expr = FunctionCall("ISNUMBER", [Identifier(["val"])])
    assert await evaluate_expr(expr, resolver) is True

    # ISNUMBER(text) -> False
    expr2 = FunctionCall("ISNUMBER", [Identifier(["text"])])
    assert await evaluate_expr(expr2, resolver) is False

async def test_evaluate_isblank():
    resolver = DictResolver({"val": None, "empty": "", "full": "abc"})
    
    # ISBLANK(val) -> True
    expr = FunctionCall("ISBLANK", [Identifier(["val"])] )
    assert await evaluate_expr(expr, resolver) is True

    # ISBLANK(empty) -> True
    expr2 = FunctionCall("ISBLANK", [Identifier(["empty"])] )
    assert await evaluate_expr(expr2, resolver) is True

    # ISBLANK(full) -> False
    expr3 = FunctionCall("ISBLANK", [Identifier(["full"])] )
    assert await evaluate_expr(expr3, resolver) is False

async def test_evaluate_subtraction():
    resolver = DictResolver({})
    expr = BinaryOp(Number(10), "-", Number(4))
    assert await evaluate_expr(expr, resolver) == 6.0

async def test_evaluate_division():
    resolver = DictResolver({})
    expr = BinaryOp(Number(10), "/", Number(2))
    assert await evaluate_expr(expr, resolver) == 5.0

async def test_evaluate_coalesce():
    resolver = DictResolver({"a": None, "b": "", "c": "found"})
    # COALESCE(a, b, c) -> "found"
    expr = FunctionCall("COALESCE", [
        Identifier(["a"]),
        Identifier(["b"]),
        Identifier(["c"])
    ])
    assert await evaluate_expr(expr, resolver) == "found"

    # COALESCE(a) -> None
    expr2 = FunctionCall("COALESCE", [Identifier(["a"])])
    assert await evaluate_expr(expr2, resolver) is None

async def test_evaluate_power():
    resolver = DictResolver({})
    expr = FunctionCall("POWER", [Number(2), Number(3)])
    assert await evaluate_expr(expr, resolver) == 8.0

async def test_evaluate_ceil():
    resolver = DictResolver({})
    expr = FunctionCall("CEIL", [Number(1.1)])
    assert await evaluate_expr(expr, resolver) == 2

async def test_evaluate_floor():
    resolver = DictResolver({})
    expr = FunctionCall("FLOOR", [Number(1.9)])
    assert await evaluate_expr(expr, resolver) == 1

async def test_evaluate_round():
    resolver = DictResolver({})
    # ROUND(1.5) -> 2
    expr = FunctionCall("ROUND", [Number(1.5)])
    assert await evaluate_expr(expr, resolver) == 2

    # ROUND(1.234, 2) -> 1.23
    expr2 = FunctionCall("ROUND", [Number(1.234), Number(2)])
    assert await evaluate_expr(expr2, resolver) == 1.23

async def test_evaluate_aggregate_functions():
    resolver = DictResolver({})
    # SUM(1, 2, 3) -> 6
    expr = FunctionCall("SUM", [Number(1), Number(2), Number(3)])
    assert await evaluate_expr(expr, resolver) == 6

    # ANY(0, 1) -> True
    expr2 = FunctionCall("ANY", [Number(0), Number(1)])
    assert await evaluate_expr(expr2, resolver) is True

    # AVERAGE(2, 4) -> 3
    expr3 = FunctionCall("AVERAGE", [Number(2), Number(4)])
    assert await evaluate_expr(expr3, resolver) == 3

    # MAX(1, 5, 2) -> 5
    expr4 = FunctionCall("MAX", [Number(1), Number(5), Number(2)])
    assert await evaluate_expr(expr4, resolver) == 5

    # MIN(1, 5, 2) -> 1
    expr5 = FunctionCall("MIN", [Number(1), Number(5), Number(2)])
    assert await evaluate_expr(expr5, resolver) == 1

    # COUNT("a", "", "b", None) -> 2
    expr6 = FunctionCall("COUNT", [String("a"), String(""), String("b"), String("")]) 
    assert await evaluate_expr(expr6, resolver) == 2

    # COUNTDISTINCT("a", "b", "a") -> 2
    expr7 = FunctionCall("COUNTDISTINCT", [String("a"), String("b"), String("a")])
    assert await evaluate_expr(expr7, resolver) == 2

async def test_evaluate_string_functions():
    resolver = DictResolver({})
    
    # TEXT(123) -> "123.0" (float)
    expr = FunctionCall("TEXT", [Number(123.0)])
    assert await evaluate_expr(expr, resolver) == "123.0"

    # VALUE("123") -> 123.0
    expr2 = FunctionCall("VALUE", [String("123")])
    assert await evaluate_expr(expr2, resolver) == 123.0

    # LOWER("ABC") -> "abc"
    expr3 = FunctionCall("LOWER", [String("ABC")])
    assert await evaluate_expr(expr3, resolver) == "abc"

    # TRIM("  abc  ") -> "abc"
    expr4 = FunctionCall("TRIM", [String("  abc  ")])
    assert await evaluate_expr(expr4, resolver) == "abc"

    # CONCAT("a", "b") -> "ab"
    expr5 = FunctionCall("CONCAT", [String("a"), String("b")])
    assert await evaluate_expr(expr5, resolver) == "ab"

    # LEFT("abc", 1) -> "a"
    expr6 = FunctionCall("LEFT", [String("abc"), Number(1)])
    assert await evaluate_expr(expr6, resolver) == "a"

    # RIGHT("abc", 1) -> "c"
    expr7 = FunctionCall("RIGHT", [String("abc"), Number(1)])
    assert await evaluate_expr(expr7, resolver) == "c"

    # MID("abc", 2, 1) -> "b"
    expr8 = FunctionCall("MID", [String("abc"), Number(2), Number(1)])
    assert await evaluate_expr(expr8, resolver) == "b"

async def test_evaluate_search():
    resolver = DictResolver({})
    # SEARCH("b", "abc") -> 2
    expr = FunctionCall("SEARCH", [String("b"), String("abc")])
    assert await evaluate_expr(expr, resolver) == 2
    
    # SEARCH("b", "abc", 3) -> None (not found starting at 3)
    expr2 = FunctionCall("SEARCH", [String("b"), String("abc"), Number(3)])
    assert await evaluate_expr(expr2, resolver) is None

async def test_evaluate_regex_functions():
    resolver = DictResolver({})
    
    # REGEXMATCH("abc", "^a") -> True
    expr = FunctionCall("REGEXMATCH", [String("abc"), String("^a")])
    assert await evaluate_expr(expr, resolver) is True

    # REGEXEXTRACT("abc123def", "\\d+") -> "123"
    expr2 = FunctionCall("REGEXEXTRACT", [String("abc123def"), String("\\d+")])
    assert await evaluate_expr(expr2, resolver) == "123"

    # REGEXREPLACE("abc", "a", "z") -> "zbc"
    expr3 = FunctionCall("REGEXREPLACE", [String("abc"), String("a"), String("z")])
    assert await evaluate_expr(expr3, resolver) == "zbc"

async def test_evaluate_edge_cases():
    resolver = DictResolver({})

    # MAX() -> None
    expr = FunctionCall("MAX", [])
    assert await evaluate_expr(expr, resolver) is None

    # MIN() -> None
    expr2 = FunctionCall("MIN", [])
    assert await evaluate_expr(expr2, resolver) is None
    
    # MAX(1, "a") -> None (TypeError handled)
    expr3 = FunctionCall("MAX", [Number(1), String("a")])
    assert await evaluate_expr(expr3, resolver) is None

    # AVERAGE("a", "b") -> 0
    expr4 = FunctionCall("AVERAGE", [String("a"), String("b")])
    assert await evaluate_expr(expr4, resolver) == 0

    # VALUE("abc") -> None
    expr5 = FunctionCall("VALUE", [String("abc")])
    assert await evaluate_expr(expr5, resolver) is None
    
    # REGEXEXTRACT("abc", "\\d+") -> None
    expr6 = FunctionCall("REGEXEXTRACT", [String("abc"), String("\\d+")])
    assert await evaluate_expr(expr6, resolver) is None

    # MID("abc", 0, 1) -> "a" (start < 1 clamped to 1)
    expr7 = FunctionCall("MID", [String("abc"), Number(0), Number(1)])
    assert await evaluate_expr(expr7, resolver) == "a"

async def test_evaluate_originating_identifier():
    data = {"name": "current"}
    originating = {"name": "originating"}
    resolver = DictResolver(data, originating_data=originating)
    
    assert await evaluate_expr(Identifier(["name"], originating=False), resolver) == "current"
    assert await evaluate_expr(Identifier(["name"], originating=True), resolver) == "originating"

async def test_evaluate_lookup_with_mock():
    class MockLookupResolver:
        async def resolve(self, identifier):
            return "val"

        async def lookup(self, form_id, criteria, expression):
            return f"looked_up_{form_id}"

        async def aggregate(self, function, form_id, criteria, expression):
            return f"aggregated_{function}_{form_id}"

    resolver = MockLookupResolver()

    expr = FunctionCall("LOOKUP", [String("form1"), Number(1), Number(2)])
    assert await evaluate_expr(expr, resolver) == "looked_up_form1"

    expr2 = FunctionCall("AGGREGATE", [String("SUM"), String("form1"), Number(1), Number(2)])
    assert await evaluate_expr(expr2, resolver) == "aggregated_SUM_form1"
