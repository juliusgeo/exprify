import ast
import inspect

from .ast_transformer import StatementMapper
from .injections import injected_ast_objs


def transpile(source):
    mapper = StatementMapper()
    a = mapper.generic_visit(ast.parse(source))
    a.body = [ast.Expr(value=node) for node in a.body]
    if mapper.required_injects:
        for inject in mapper.required_injects:
            a.body.insert(0, injected_ast_objs[inject])
    a = ast.fix_missing_locations(a)
    return a


def transpiled_function_ast(func, debug=False):
    a = transpile(inspect.getsource(func))
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


def transpiled_function_object(func, debug=False):
    a = transpiled_function_ast(func, debug)
    namespace = {}
    compiled_ast = compile(a, filename="", mode="exec")
    exec(compiled_ast, namespace)
    return namespace[func.__name__]


def transpile_script_source(src):
    a = transpile(src)
    unparsed = ast.unparse(a)
    return unparsed
