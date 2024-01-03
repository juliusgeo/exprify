from collections import namedtuple

from exprify import transpile_script_source
from itertools import groupby
from keyword import iskeyword
from tokenize import NAME, STRING, tokenize
import tokenize as tk
import io
import python_minifier


TOLERANCE = 4
# We only need these attributes from the Token namedtuples defined in the tokenize module
Token = namedtuple("Token", ["string", "type"])


def partition_token(tok, space):
    ts = tok.string
    splpt = ts.find(".") if tok.type == NAME else space
    # Checks to make sure we aren't in the middle of an f-string
    if "f'" in ts:
        for i in range(space - TOLERANCE, space + TOLERANCE + 1):
            if ts[:i].count("{") == ts[:i].count("}"):
                splpt = i
    septok = "" if tok.type == NAME else "'"
    return Token(string=ts[:splpt] + septok, type=tok.type), Token(
        string=septok + ts[splpt:], type=tok.type
    )


def generate_whitespace_groups(line):
    return [
        (is_space, len(list(group)))
        for is_space, group in groupby(line, key=str.isspace)
    ]


def reflow(script, outline):
    # Minify script and then transpile it
    with open(script, "r") as f:
        script = f.read()
        script = python_minifier.minify(
            script,
            rename_locals=True,
            rename_globals=True,
            hoist_literals=True,
            remove_annotations=True,
        )
        script = transpile_script_source(script)

    old, *token_list = [
        Token(tok.string.strip(), tok.type)
        for tok in tokenize(io.BytesIO(bytes(script, "utf-8")).readline)
    ]
    new_lines = "(\n);"

    for line in open(outline).readlines():
        line = line.rstrip()
        cur_line = ""
        carry_over = 0
        for is_whitespace, num_chars in generate_whitespace_groups(line):
            if is_whitespace:
                cur_line += " " * (num_chars + carry_over)
            else:
                space = num_chars
                while space > 0:
                    if not token_list:
                        break
                    if len(token_list[0].string.strip()) > space + TOLERANCE:
                        if token_list[0].type in (STRING, NAME):
                            # We can't split NAMEs if they don't have a dot in them
                            if (
                                token_list[0].type == NAME
                                and "." not in token_list[0].string
                            ):
                                break
                            # If the string is too long, split it up
                            left, right = partition_token(token_list.pop(0), space)
                            token_list.insert(0, right)
                            cur_token = left
                        elif (
                            old.type == STRING
                            or token_list[0].type == STRING
                            and space > 0
                        ):
                            # If the previous token was a string, we can just append "" to the end of it, which will be ignored
                            cur_token = Token(string="", type=STRING)
                        else:
                            # We can't resize, so continue to the next group :(
                            break
                    else:
                        cur_token = token_list.pop(0)
                    tok_str = cur_token.string.strip()
                    match cur_token.type:
                        case tk.NEWLINE:
                            tok_str = tok_str + ";"
                        case tk.NL:
                            tok_str = ""
                        case _:
                            # Need to add a space between NAMES and (keywords or NAMES)
                            if (
                                iskeyword(tok_str) or cur_token.type == NAME
                            ) and old.type == NAME:
                                if cur_line and cur_line[-1] != " ":
                                    tok_str = " " + tok_str
                                elif (
                                    not cur_line and new_lines and new_lines[-1] != " "
                                ):
                                    tok_str = " " + tok_str
                    old = cur_token
                    space -= len(tok_str)
                    cur_line += tok_str
                carry_over = space
        if len(token_list) > 0:
            cur_line = cur_line + "\\\n"
        if cur_line:
            new_lines += cur_line
    return "".join(new_lines)
