import ast


class StatementMapper(ast.NodeTransformer):
    top_level_funcdef = True

    def visit_If(self, node):
        return ast.IfExp(
            test=node.test,
            body=self.map_body(node),
            orelse=self.map_stmt(node.orelse[0]),
        )

    def visit_AugAssign(self, node):
        if isinstance(node.target, ast.Name):
            target_load=ast.Name(id=node.target.id,ctx=ast.Load())
        elif isinstance(node.target, ast.Attribute):
            target_load=ast.Attribute(value=node.target.value, attr=node.target.attr, ctx=ast.Load())
        return ast.NamedExpr(
            target=node.target,
            value=ast.BinOp(left=target_load, op=node.op, right=node.value),
        )

    def visit_ImportFrom(self, node):
        imps = []
        module = ast.Call(
            func=ast.Name(id="__import__", ctx=ast.Load()),
            args=[ast.Constant(value=node.module)],
            keywords=[],
        )
        for name in node.names:
            imps.append(
                ast.NamedExpr(
                    target=ast.Name(id=name.name, ctx=ast.Store()),
                    value=ast.Call(
                        func=ast.Name(id="getattr", ctx=ast.Load()),
                        args=[module, ast.Constant(value=name.name)],
                        keywords=[],
                    ),
                )
            )

        return ast.Tuple(elts=imps, ctx=ast.Load())

    def visit_Import(self, node):
        # Replace imports with __import__ calls
        imps = []
        for name in node.names:
            imps.append(
                ast.NamedExpr(
                    target=ast.Name(id=name.name, ctx=ast.Store()),
                    value=ast.Call(
                        func=ast.Name(id="__import__", ctx=ast.Load()),
                        args=[ast.Constant(value=name.name)],
                        keywords=[],
                    ),
                )
            )

        return ast.Tuple(elts=imps, ctx=ast.Load())

    def visit_Assign(self, node):
        if len(node.targets) == 1:
            return ast.NamedExpr(target=node.targets[0], value=node.value)
        targets = []
        for target in node.targets:
            targets.append(ast.NamedExpr(target=target, value=node.value))
        return ast.Tuple(elts=targets, ctx=ast.Load())

    def visit_For(self, node):
        return ast.ListComp(
            elt=self.map_body(node),
            generators=[
                ast.comprehension(
                    target=ast.Name(id="_", ctx=ast.Store()),
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
        return node

    def visit_Expr(self, node):
        return node.value

    def map_stmt(self, node):
        if isinstance(node, list):
            return ast.Tuple(elts=[self.map_stmt(j) for j in node], ctx=ast.Load())
        return self.visit(node)

    def map_body(self, node):
        statements = [self.map_stmt(i) for i in node.body]
        # If we have multiple statements, and the last statement is a return, then we will need to slice the tuple that represents the results of the
        # lambda function we're inserting. This is necessary because lambda functions return the result of the expression inside of them. Because we're
        # representing the entire function body as a tuple, normally it would just return the tuple.
        if ast.Return is type(statements[-1]):
            if len(statements) > 1:
                statements[-1] = self.map_stmt(statements[-1].value)

            else:
                # If there is only one statement, and it's a return, we don't need the subscript.
                return statements[-1].value
        else:
            # If there isn't a return at the end, we need to return None.
            statements.append(ast.Constant(value=None))
        return ast.Subscript(
            ast.Tuple(elts=statements,ctx=ast.Load()),
            slice=ast.UnaryOp(op=ast.USub(),operand=ast.Constant(value=1)),
            ctx=ast.Load(),
        )
    def visit_ClassDef(self, node):
        class_body_dict = {}
        for subnode in node.body:
            if isinstance(subnode, ast.FunctionDef):
                class_body_dict[subnode.name] = self.visit_FunctionDef(subnode, class_def=True)
            elif isinstance(subnode, ast.Assign):
                for target in subnode.targets:
                    class_body_dict[target.id] = subnode.value
        class_body = ast.Dict(keys=[ast.Constant(value=k) for k in class_body_dict.keys()], values=[v for v in class_body_dict.values()])
        return ast.NamedExpr(
            target=ast.Name(id=node.name,ctx=ast.Store()),
            value=ast.Call(
                func=ast.Name(id="type",ctx=ast.Load()),
                args=[ast.Constant(value=node.name), ast.Tuple(elts=[], ctx=ast.Load()), class_body],
                keywords=[],
            ),
        )
    def visit_FunctionDef(self, node, class_def=False):
        # If the function is top level, we want to use normal assignment. Otherwise, has to be a named expression.
        if self.top_level_funcdef:
            self.top_level_funcdef = False
            function_body = self.map_body(node)
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
