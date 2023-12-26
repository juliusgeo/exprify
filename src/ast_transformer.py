import ast


class StatementMapper(ast.NodeTransformer):
    top_level_funcdef = True

    def visit_If(self, node):
        return ast.IfExp(
            test=node.test,body=self.map_body(node),orelse=self.map_stmt(node.orelse[0])
        )
    
    def visit_AugAssign(self, node):
        target_load=ast.Name(id=node.target.id,ctx=ast.Load())
        return ast.NamedExpr(
            target=node.target,
            value=ast.BinOp(left=target_load,op=node.op,right=node.value),
        )

    def visit_Assign(self, node):
        if len(node.targets)==1:
            return ast.NamedExpr(target=node.targets[0],value=node.value)
        targets=[]
        for target in node.targets:
            targets.append(ast.NamedExpr(target=target,value=node.value))
        return ast.Tuple(elts=targets,ctx=ast.Load())

    def visit_For(self, node):
        return ast.ListComp(
            elt=self.map_body(node),
            generators=[
                ast.comprehension(
                    target=ast.Name(id="_",ctx=ast.Store()),
                    iter=node.iter,
                    is_async=False,
                    ifs=[],
                )
            ],
        )

    def visit_While(self, node):
        condition=node.test
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
            elt=self.map_body(node),
            generators=[
                ast.comprehension(
                    target=ast.Name(id="_",ctx=ast.Store()),
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
        statements = []

        for i in node.body:
            statements.append(self.map_stmt(i))
        if ast.Return is type(statements[-1]):
            if len(statements) > 1:
                statements[-1] = self.map_stmt(statements[-1].value)
                return ast.Subscript(
                    ast.Tuple(elts=statements, ctx=ast.Load()),
                    slice=ast.UnaryOp(op=ast.USub(), operand=ast.Constant(value=1)),
                    ctx=ast.Load(),
                )
            else:
                return statements[-1].value
        return ast.Tuple(elts=statements, ctx=ast.Load())

    def visit_FunctionDef(self, node):
        if self.top_level_funcdef:
            self.top_level_funcdef=False
            function_body=self.map_body(node)
            return ast.Assign(
                targets=[ast.Name(id=node.name,ctx=ast.Store())],
                value=ast.Lambda(args=node.args,body=function_body),
            )
        else:
            function_body=self.map_body(node)
            return ast.NamedExpr(
                target=ast.Name(id=node.name,ctx=ast.Store()),
                value=ast.Lambda(args=node.args,body=function_body),
            )

