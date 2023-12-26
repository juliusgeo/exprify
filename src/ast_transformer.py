import ast
import inspect


class StatementMapper(ast.NodeTransformer):
    def map_stmt(self, i):
        if isinstance(i, list):
            return ast.Tuple(elts=[self.map_stmt(j) for j in i], ctx=ast.Load())
        if isinstance(i, ast.If):
            return ast.IfExp(
                test=i.test, body=self.map_body(i), orelse=self.map_stmt(i.orelse[0])
            )
        if isinstance(i, ast.AugAssign):
            target_load = ast.Name(id=i.target.id, ctx=ast.Load())
            return ast.NamedExpr(
                target=i.target,
                value=ast.BinOp(left=target_load, op=i.op, right=i.value),
            )
        if isinstance(i, ast.Assign):
            if len(i.targets) == 1:
                return ast.NamedExpr(target=i.targets[0], value=i.value)
            targets = []
            for target in i.targets:
                targets.append(ast.NamedExpr(target=target, value=i.value))
            return ast.Tuple(elts=targets, ctx=ast.Load())
        if isinstance(i, ast.For):
            return ast.ListComp(
                elt=self.map_body(i),
                generators=[
                    ast.comprehension(
                        target=ast.Name(id="_", ctx=ast.Store()),
                        iter=i.iter,
                        is_async=False,
                        ifs=[],
                    )
                ],
            )
        if isinstance(i, ast.While):
            condition  = i.test
            iterator=ast.Call(
                func=ast.Name(id='iter',ctx=ast.Load()),
                args=[
                    ast.Lambda(
                        args=ast.arguments(
                            posonlyargs=[],
                            args=[],
                            kwonlyargs=[],
                            kw_defaults=[],
                            defaults=[]),
                        body=condition),
                    ast.Constant(value=False)],
                keywords=[])

            return ast.ListComp(
                elt=self.map_body(i),
                generators=[
                    ast.comprehension(
                        target=ast.Name(id="_", ctx=ast.Store()),
                        iter=iterator,
                        is_async=False,
                        ifs=[],
                    )
                ],
            )
        if isinstance(i, ast.Return):
            return i
        if isinstance(i, ast.Expr):
            return i.value
        return i

    def map_body(self, node):
        statements = []
        if len(node.body) == 1:
            return self.map_stmt(node.body[0])
        for i in node.body:
            statements.append(self.map_stmt(i))
        if ast.Return == type(statements[-1]):
            statements[-1] = statements[-1].value
            return ast.Subscript(
                ast.Tuple(elts=statements, ctx=ast.Load()),
                slice=ast.UnaryOp(op=ast.USub(), operand=ast.Constant(value=1)),
                ctx=ast.Load(),
            )
        return ast.Tuple(elts=statements, ctx=ast.Load())

    def visit_FunctionDef(self, node):
        function_body = self.map_body(node)
        return ast.Assign(
            targets=[ast.Name(id=node.name, ctx=ast.Store())],
            value=ast.Lambda(args=node.args, body=function_body),
        )
