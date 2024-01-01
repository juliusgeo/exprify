from exprify import transpile_script_source
from itertools import groupby
from collections import namedtuple
from keyword import iskeyword
from tokenize import NEWLINE, NL, NAME, STRING, tokenize
import io
import python_minifier


ns = ["(\n);"]
app, tol = ns.append, 6
attr = getattr


def reflow(script, outline):
    with open(script, "r") as f:
        script = transpile_script_source(f.read())
        script = python_minifier.minify(
            script,
            rename_locals=False,
            rename_globals=True,
            hoist_literals=True,
            remove_annotations=True,
        )
    old, *token_list = tokenize(io.BytesIO(bytes(script, "utf-8")).readline)
    tok_lt = {
        NEWLINE: lambda z, v: app(";") if ns[-1] != ";" else None,
        NL: lambda z, v: app("") if ns[-1] != ";" else None,
    }
    toktup = namedtuple("t", ["string", "type"])

    def partition_token(tok, space):
        ts = "".join(tok.string.split(" "))
        splpt = ts.find(".") if tok.type == NAME else space - tol
        septok = "" if tok.type == NAME else '"'
        return toktup(string=ts[:splpt] + septok, type=tok.type), toktup(
            string=('"' if tok.type == STRING else "") + ts[splpt:], type=tok.type
        )

    for line in open(outline).readlines():
        t_buf = 0
        for sp, gr in groupby(line, key=str.isspace):
            if sp:
                app("".join(list(gr)[t_buf:]))
            else:
                # print(list(gr)[t_buf:])
                space = len(list(gr)[t_buf:])
                for i in range(min(space, len(token_list))):
                    b = len(" ".join(token_list[0].string.split())) - tol
                    if space >= b:
                        t_buf = -1 * b
                        tok = token_list.pop(0)
                        tok1, tok2 = partition_token(tok, space)
                        if tok.type in (NAME, STRING) and (
                            "." in tok.string and len(tok.string) >= space
                        ):
                            cs = tok1.string
                            if len(tok2.string) > 0 or "." in tok.string:
                                token_list.insert(0, tok2)
                        else:
                            cs = " ".join(tok.string.split())
                        cur_len = len(cs)
                        tok_lt.get(
                            tok.type,
                            lambda tok, old: app(" " + cs)
                            if iskeyword(cs) or (old.type == NAME and tok.type == NAME)
                            else app(cs),
                        )(tok, old)
                        old = tok
                        space = space - cur_len
        if token_list:
            ns.append(ns.pop(-1).strip() + "\\\n")
        if any(isinstance(i, tuple) for i in ns):
            print(ns)
            break

    return "".join(ns)
