import ast
import inspect

from .ast_transformer import StatementMapper


def transpiled_function_object(func, debug=False):
    a = transpiled_function_ast(func, debug)[0]
    namespace = {}
    compiled_ast = compile(a, filename="", mode="exec")
    exec(compiled_ast, namespace)
    return namespace[func.__name__]


def transpiled_function_ast(func, debug=False):
    mapper = StatementMapper()
    a = mapper.generic_visit(ast.parse(inspect.getsource(func)))
    a = ast.fix_missing_locations(a)
    src = ""
    if debug:
        ref = ast.dump(ast.parse(inspect.getsource(func)), indent=1)
        gen = ast.dump(a, indent=1)
        print("Reference:\n", ref)
        print("Generated:\n", gen)
        src = ast.unparse(a)
        print(src)
    return a, src


def transpiled_script(filename):
    with open(filename, "r") as f:
        src = f.read()
        mapper = StatementMapper()
        print(type(ast.parse(src)))
        a = mapper.generic_visit(ast.parse(src))
        a.body = [ast.Expr(value=node) for node in a.body]
        a = ast.fix_missing_locations(a)
        print(ast.unparse(a))
        compiled_ast = compile(ast.unparse(a), filename="", mode="exec")
        namespace = {}
        exec(compiled_ast, namespace)
        return a
