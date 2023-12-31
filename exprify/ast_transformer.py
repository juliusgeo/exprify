import ast
import itertools

intermediate_gen = itertools.count(1)


class ExprifyException(Exception):
    pass


class StatementMapper(ast.NodeTransformer):
    top_level = True

    def visit_If(self, node):
        return ast.IfExp(
            test=node.test,
            body=self.map_body(node),
            orelse=self.map_body(node.orelse),
        )

    def visit_With(self, node):
        # For each of the context managers, we need to prepend and append the __enter__ and __exit__ calls, respectively.
        enters = []
        for ctx_manager in node.items:
            c = ast.Call(
                func=ast.Name(id="getattr", ctx=ast.Load()),
                args=[ctx_manager.context_expr, ast.Constant(value="__enter__")],
                keywords=[],
            )
            if ctx_manager.optional_vars:
                enters.append(
                    ast.NamedExpr(
                        target=ctx_manager.optional_vars,
                        value=ast.Call(func=c, args=[], keywords=[]),
                    )
                )
            else:
                enters.append(ctx_manager.context_expr)
        exits = []
        for ctx_manager in node.items:
            exits.append(
                ast.Call(
                    func=ast.Call(
                        func=ast.Name(id="getattr", ctx=ast.Load()),
                        args=[ctx_manager.context_expr, ast.Constant(value="__exit__")],
                        keywords=[],
                    ),
                    args=[],
                    keywords=[],
                )
            )
        # We don't want to be returning any of the exits, so index the body tuple so we just get the values
        # from self.map_body
        return ast.Subscript(
            value=ast.Tuple(
                elts=enters + [self.map_body(node)] + exits, ctx=ast.Load()
            ),
            slice=ast.Constant(value=len(enters)),
            ctx=ast.Load(),
        )

    def visit_AugAssign(self, node):
        # Target can either be a name, or a class attribute
        if isinstance(node.target, ast.Name):
            target_load = ast.Name(id=node.target.id, ctx=ast.Load())
        elif isinstance(node.target, ast.Attribute):
            target_load = ast.Attribute(
                value=node.target.value, attr=node.target.attr, ctx=ast.Load()
            )
            return ast.Call(
                func=ast.Name(id="setattr", ctx=ast.Load()),
                args=[
                    node.target.value,
                    ast.Constant(value=node.target.attr),
                    ast.BinOp(left=target_load, op=node.op, right=node.value),
                ],
                keywords=[],
            )

        return ast.NamedExpr(
            target=node.target,
            value=ast.BinOp(left=target_load, op=node.op, right=node.value),
        )

    def import_Helper(self, node, imp_gen):
        imps = [imp_gen(name) for name in node.names]
        if len(imps) > 1:
            return ast.Tuple(elts=imps, ctx=ast.Load())
        else:
            return ast.Expr(value=imps[0])

    def visit_ImportFrom(self, node):
        # Replace from library import function with getattr(__import__(library), function) calls
        def imp_gen(name):
            module = ast.Call(
                func=ast.Name(id="__import__", ctx=ast.Load()),
                args=[ast.Constant(value=node.module)],
                keywords=[],
            )
            as_name = name.asname if name.asname else name.name
            return ast.NamedExpr(
                target=ast.Name(id=as_name, ctx=ast.Store()),
                value=ast.Call(
                    func=ast.Name(id="getattr", ctx=ast.Load()),
                    args=[module, ast.Constant(value=name.name)],
                    keywords=[],
                ),
            )

        return self.import_Helper(node, imp_gen)

    def visit_Import(self, node):
        # Replace imports with __import__ calls
        def imp_gen(name):
            as_name = name.asname if name.asname else name.name
            return ast.NamedExpr(
                target=ast.Name(id=as_name, ctx=ast.Store()),
                value=ast.Call(
                    func=ast.Name(id="__import__", ctx=ast.Load()),
                    args=[ast.Constant(value=name.name)],
                    keywords=[],
                ),
            )

        return self.import_Helper(node, imp_gen)

    def visit_Assign(self, node):
        if self.top_level:
            return node
        if len(node.targets) == 1:
            if isinstance(node.targets[0], ast.Tuple):
                intermediate_name = f"inter{next(intermediate_gen)}"
                intermediate = ast.NamedExpr(
                    target=ast.Name(id=intermediate_name, ctx=ast.Store()),
                    value=node.value,
                )
                targets = [intermediate] + [
                    ast.NamedExpr(
                        target=target,
                        value=ast.Subscript(
                            ast.Name(id=intermediate_name, ctx=ast.Load()),
                            slice=ast.Constant(value=index),
                            ctx=ast.Load(),
                        ),
                    )
                    for index, target in enumerate(node.targets[0].elts)
                ]
            else:
                if isinstance(node.targets[0], ast.Name):
                    return ast.NamedExpr(target=node.targets[0], value=node.value)
                elif isinstance(node.targets[0], ast.Attribute):
                    return ast.Call(
                        func=ast.Name(id="setattr", ctx=ast.Load()),
                        args=[
                            node.targets[0].value,
                            ast.Constant(value=node.targets[0].attr),
                            node.value,
                        ],
                        keywords=[],
                    )
        else:
            targets = [
                ast.NamedExpr(target=target, value=node.value)
                for target in node.targets
            ]
        return ast.List(elts=targets, ctx=ast.Load())

    def visit_For(self, node):
        return ast.ListComp(
            elt=self.map_body(node),
            generators=[
                ast.comprehension(
                    target=node.target,
                    iter=node.iter,
                    is_async=False,
                    ifs=[],
                )
            ],
        )

    def visit_While(self, node):
        condition = node.test
        # This is an ast equivalent of iter(lambda: condition, False), which will produce true (potentially infinitely)
        # until condition is false. This nicely sidesteps having to use takewhile, or other equivalents for emulating while loops
        # in list comprehensions.
        iterator = ast.Call(
            func=ast.Name(id="iter", ctx=ast.Load()),
            args=[
                ast.Lambda(
                    args=ast.arguments(
                        posonlyargs=[],
                        args=[],
                        kwonlyargs=[],
                        kw_defaults=[],
                        defaults=[],
                    ),
                    body=condition,
                ),
                ast.Constant(value=False),
            ],
            keywords=[],
        )

        return ast.ListComp(
            elt=self.map_body(node),
            generators=[
                ast.comprehension(
                    target=ast.Name(id="_", ctx=ast.Store()),
                    iter=iterator,
                    is_async=False,
                    ifs=[],
                )
            ],
        )

    def visit_Return(self, node):
        return node.value

    def visit_Expr(self, node):
        return self.visit(node.value)

    def map_stmt(self, node):
        if isinstance(node, list):
            return ast.List(elts=[self.map_stmt(j) for j in node], ctx=ast.Load())
        return self.visit(node)

    def map_body(self, node):
        # Convert the bodies of functions/if statements to tuples with expressions inside.
        # Because lambda functions always return the entirety of the expression inside them, because we are getting a tuple
        # of the statements converted into expressions, we need to index into the last element so that it returns the result
        # rather than the whole tuple.

        # If node is from an If-orelse, it will be a list, not a node with a body.
        body = node if isinstance(node, list) else node.body
        statements = [self.map_stmt(i) for i in body]

        # If there's nothing in the body, return None.
        if not statements or statements[0] is None:
            return ast.Constant(value=None)

        # If there's only one expression in the body, just return that. Otherwise, return a tuple
        # indexed to the last element so that the lambda func returns the last value.
        if len(statements) == 1:
            return statements[0]
        else:
            return ast.Subscript(
                ast.List(elts=statements, ctx=ast.Load()),
                slice=ast.UnaryOp(op=ast.USub(), operand=ast.Constant(value=1)),
                ctx=ast.Load(),
            )

    def visit_ClassDef(self, node):
        class_body_dict = {}
        for subnode in node.body:
            if isinstance(subnode, ast.FunctionDef):
                class_body_dict[subnode.name] = self.visit_FunctionDef(
                    subnode, class_def=True
                )
            elif isinstance(subnode, ast.Assign):
                for target in subnode.targets:
                    class_body_dict[target.id] = subnode.value
        class_body = ast.Dict(
            keys=[ast.Constant(value=k) for k in class_body_dict.keys()],
            values=[v for v in class_body_dict.values()],
        )
        return ast.NamedExpr(
            target=ast.Name(id=node.name, ctx=ast.Store()),
            value=ast.Call(
                func=ast.Name(id="type", ctx=ast.Load()),
                args=[
                    ast.Constant(value=node.name),
                    ast.Tuple(elts=[], ctx=ast.Load()),
                    class_body,
                ],
                keywords=[],
            ),
        )

    def visit_FunctionDef(self, node, class_def=False):
        # Remove type annotations
        for arg in node.args.args:
            arg.annotation = None
        # If the function is top level, we want to use normal assignment. Otherwise, has to be a named expression.
        if self.top_level:
            self.top_level = False
            function_body = self.map_body(node)
            self.top_level = True
            return ast.Assign(
                targets=[ast.Name(id=node.name, ctx=ast.Store())],
                value=ast.Lambda(args=node.args, body=function_body),
            )
        else:
            function_body = self.map_body(node)
            lambda_func = ast.Lambda(args=node.args, body=function_body)
            if class_def:
                return lambda_func
            return ast.NamedExpr(
                target=ast.Name(id=node.name, ctx=ast.Store()),
                value=lambda_func,
            )

    def visit_Continue(self, node):
        raise ExprifyException("Exprify does not support 'continue'")

    def visit_Break(self, node):
        raise ExprifyException("Exprify does not support 'break'")

    def visit_Yield(self, node):
        raise ExprifyException("Exprify does not support 'yield'")

    def visit_YieldFrom(self, node):
        raise ExprifyException("Exprify does not support 'yield'")

    def visit_Delete(self, node):
        raise ExprifyException("Exprify does not support 'del'")

    def visit_Pass(self, node):
        raise ExprifyException("Exprify does not support 'pass'")

    def visit_Try(self, node):
        raise ExprifyException("Exprify does not support 'try'")

    def visit_TryStar(self, node):
        raise ExprifyException("Exprify does not support 'try'")

    def visit_Raise(self, node):
        raise ExprifyException("Exprify does not support 'raise")

    def visit_AsyncFunctionDef(self, node):
        raise ExprifyException("Exprify does not support async")

    def visit_AsyncWith(self, node):
        raise ExprifyException("Exprify does not support async")

    def visit_AsyncFor(self, node):
        raise ExprifyException("Exprify does not support async")

    def visit_Nonlocal(self, node):
        raise ExprifyException("Exprify does not support nonlocal")

    def visit_Global(self, node):
        raise ExprifyException("Exprify does not support global")
