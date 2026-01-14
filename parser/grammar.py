GRAMMAR = r"""
?start: expr

?expr: logical_or

?logical_or: logical_and
           | logical_or "||" logical_and -> or_op

?logical_and: comparison
            | logical_and "&&" comparison -> and_op

?comparison: sum
           | sum COMP_OP sum -> comparison_op

?sum: product
    | sum "+" product -> add_op
    | sum "-" product -> sub_op

?product: atom
        | product "*" atom -> mul_op
        | product "/" atom -> div_op

?atom: dotted_name
     | NUMBER
     | STRING
     | "!" atom -> not_op
     | function_call
     | "(" expr ")"

function_call: NAME "(" [expr ("," expr)*] ")"

dotted_name: NAME ("." NAME)*

COMP_OP: "==" | "!=" | "<=" | ">=" | "<" | ">"

%import common.CNAME -> NAME
%import common.NUMBER
%import common.ESCAPED_STRING -> STRING
%import common.WS
%ignore WS
"""