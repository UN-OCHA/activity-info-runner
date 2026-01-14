GRAMMAR = r"""
?start: expr

?expr: comparison
     | sum

comparison: dotted_name OP value

?sum: product
    | sum "+" product

?product: atom
        | product "*" atom

?atom: dotted_name
     | NUMBER
     | "(" sum ")"

dotted_name: NAME ("." NAME)*

?value: STRING

OP: "==" | "!="

%import common.CNAME -> NAME
%import common.NUMBER
%import common.ESCAPED_STRING -> STRING
%import common.WS
%ignore WS
"""
