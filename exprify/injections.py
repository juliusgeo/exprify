from enum import StrEnum
import ast
import inspect


# ruff: noqa: F841
class Injected(StrEnum):
    RAISE = "raise"
    EXCEPT = "except"


def raise_func():
    (
        rH := lambda exc, cause=None: (
            copy := type(exc)(*exc.args),
            setattr(copy, "__cause__", cause) if cause else None,
            (_ for _ in ()).throw(copy),
        )
    )


def except_func():
    (
        ctx_dec := getattr(__import__("contextlib"), "ContextDecorator"),
        iEH := type(
            "iEH",
            ((ctx_dec,)),
            {
                "__init__": lambda iEH, except_handlers={}, final=lambda: None: [
                    setattr(iEH, "except_handlers", except_handlers),
                    setattr(iEH, "final", final),
                ][-1],
                "__enter__": lambda iEH: iEH,
                "__exit__": lambda iEH, exc_type, exc, tb: [
                    (
                        handler := (
                            [
                                handler
                                for type, handler in iEH.except_handlers.items()
                                if issubclass(exc_type, type)
                            ]
                        )
                    ),
                    ((handler or [lambda *_: None])[0](exc)),
                    (iEH.final()),
                    (handler != []),
                ][-1],
            },
        ),
    )


def get_ast_from_func(func):
    parsed = ast.parse(inspect.getsource(func))
    return parsed.body[0].body[0]


injected_ast_objs = {
    Injected.RAISE: get_ast_from_func(raise_func),
    Injected.EXCEPT: get_ast_from_func(except_func),
}
