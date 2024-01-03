import ast
import inspect

from .ast_transformer import StatementMapper


def transpiled_function_object(func, debug=False):
    a = transpiled_function_ast(func, debug)
    namespace = {}
    compiled_ast = compile(a, filename="", mode="exec")
    exec(compiled_ast, namespace)
    return namespace[func.__name__]


def transpiled_function_ast(func, debug=False):
    mapper = StatementMapper()
    a = mapper.generic_visit(ast.parse(inspect.getsource(func)))
    a = ast.fix_missing_locations(a)
    src = ast.unparse(a)
    if debug:
        ref = ast.dump(ast.parse(inspect.getsource(func)), indent=1)
        gen = ast.dump(a, indent=1)
        print("Reference:\n", ref)
        print("Generated:\n", gen)
        print(src)
    return src


def transpiled_script(filename):
    with open(filename, "r") as f:
        src = f.read()
    return transpile_script_source(src)


def transpile_script_source(src):
    mapper = StatementMapper()
    a = mapper.generic_visit(ast.parse(src))
    a.body = [ast.Expr(value=node) for node in a.body]
    a = ast.fix_missing_locations(a)
    compiled_ast = compile(ast.unparse(a), filename="", mode="exec")
    namespace = {}
    exec(compiled_ast, namespace)
    return ast.unparse(a)
