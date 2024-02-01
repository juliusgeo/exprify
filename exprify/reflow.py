from exprify import transpile_script_source
from itertools import groupby
from keyword import iskeyword
from tokenize import (
    NAME,
    STRING,
    NUMBER,
    LPAR,
    RPAR,
    LBRACE,
    RBRACE,
    LSQB,
    RSQB,
    tokenize,
    TokenInfo,
)
import tokenize as tk
import io
import python_minifier


TOLERANCE = 4


def partition_token(tok, space, tolerance):
    ts = tok.string
    splpt = ts.find(".") if tok.type == NAME else space
    septok = "" if tok.type == NAME else "'"
    left, right = ts[:splpt] + septok, septok + ts[splpt:]

    if ts.startswith("f'"):
        # Generate possible splits that wouldn't break the f-string (not inside of an embedded expression).
        # The range start is clamped so it is at minimum 2 to prevent splitting before the f-string identifier
        poss_splits = [
            (i, abs(space - i))
            for i in range(max(space - tolerance, 2), space + tolerance + 1)
            if ts[:i].count("{") == ts[:i].count("}")
        ]
        if poss_splits:
            splpt, _ = min(poss_splits, key=lambda x: x[1])
            left, right = (ts[:splpt] + "'", "f'" + ts[splpt:])
        else:
            left, right = "''", ts
    if ts.startswith("b'"):
        left, right = (ts[:splpt] + "'", "b'" + ts[splpt:])

    return TokenInfo(**tok._asdict() | dict(string=left)), TokenInfo(
        **tok._asdict() | dict(string=right)
    )


def generate_whitespace_groups(line):
    return [
        (is_space, len(list(group)))
        for is_space, group in groupby(line, key=str.isspace)
    ]


def reflow(script, outline, tolerance=TOLERANCE):
    # Minify script and then transpile it
    script = python_minifier.minify(
        script,
        rename_locals=True,
        rename_globals=True,
        hoist_literals=True,
        remove_annotations=True,
    )
    script = transpile_script_source(script)

    old, *token_list = list(tokenize(io.BytesIO(bytes(script, "utf-8")).readline))
    new_lines = "\n'';\\\n"
    implicit_line_stack = []
    implicit_line_matches = {RPAR: LPAR, RBRACE: LBRACE, RSQB: LSQB}

    for line in outline.splitlines():
        line = line.rstrip()
        cur_line = ""
        carry_over = 0
        for is_whitespace, space in generate_whitespace_groups(line):
            if is_whitespace:
                cur_line += " " * (space + carry_over)
            elif not token_list:
                cur_line += "#" * space
                carry_over = 0
            else:
                new_tokens = []
                while space > 0:
                    if not token_list:
                        cur_line += "".join(new_tokens) + "#" * space
                        new_tokens = []
                        space = 0
                        break
                    if len(token_list[0].string.strip()) > space + tolerance:
                        if token_list[0].type in (STRING, NAME):
                            # We can't split NAMEs if they don't have a dot in them
                            if (
                                token_list[0].type == NAME
                                and "." not in token_list[0].string
                            ):
                                break
                            # If the string is too long, split it up
                            left, right = partition_token(
                                token_list.pop(0), space, tolerance
                            )
                            token_list.insert(0, right)
                            cur_token = left
                        else:
                            # We can't resize, so continue to the next group :(
                            break
                    else:
                        cur_token = token_list.pop(0)
                    exact_type = cur_token.exact_type
                    tok_str = cur_token.string.strip()

                    # Stack logic to keep track of delimiters like parens
                    if exact_type in implicit_line_matches:
                        if implicit_line_matches[exact_type] == implicit_line_stack[-1]:
                            implicit_line_stack.pop(-1)
                    if exact_type in implicit_line_matches.values():
                        implicit_line_stack.append(exact_type)

                    match cur_token.type:
                        case tk.NEWLINE:
                            tok_str = tok_str + ";"
                        case tk.NL:
                            tok_str = ""
                        case _:
                            # Need to add a space between (NAMES, NUMBERS) and (keywords or NAMES)
                            if (
                                iskeyword(tok_str) or cur_token.type == NAME
                            ) and old.type in (NAME, NUMBER):
                                if new_tokens and (new_tokens[-1][-1] != " "):
                                    tok_str = " " + tok_str
                                if (
                                    cur_line
                                    and not new_tokens
                                    and (cur_line[-1] != " ")
                                ):
                                    tok_str = " " + tok_str

                    old = cur_token
                    space -= len(tok_str)
                    new_tokens.append(tok_str)
                pos = 1
                while space > 0:
                    new_tokens.insert(pos, " ")
                    space -= 1
                    pos += 1
                cur_line += "".join(new_tokens)
                carry_over = space
        # We only need to add a line continuation character when we are not inside brackets, parens, etc,
        # so check to make sure the implicit line stack is empty
        if not implicit_line_stack and token_list:
            cur_line = cur_line + "\\"
        if cur_line:
            new_lines += cur_line + "\n"
    return "".join(new_lines)
