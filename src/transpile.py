import ast, inspect

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
    if debug:
        ref = ast.dump(ast.parse(inspect.getsource(func)), indent=1)
        gen = ast.dump(a, indent=1)
        print("Reference:\n", ref)
        print("Generated:\n", gen)
        src = ast.unparse(a)
        print(src)
    return a, src