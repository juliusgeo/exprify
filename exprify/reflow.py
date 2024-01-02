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


def reflow(script, outline):
    # Transpile and THEN minify the script (doesn't work the other way for some reason).
    # Can't rename locals because python_minifier doesn't like the weird scoping of using lambdas everywhere.
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

    def partition_token(tok, space):
        ts = "".join(tok.string.split(" "))
        splpt = ts.find(".") if tok.type == NAME else space
        septok = "" if tok.type == NAME else "'"
        return Token(string=ts[:splpt] + septok, type=tok.type), Token(
            string=septok + ts[splpt:], type=tok.type
        )

    new_lines = ["(\n);"]

    def generate_whitespace_groups(line):
        # If there is a whitespace group that is a small size, then merge it into the previous non whitespace group
        groups = []
        for is_space, group in groupby(line, key=str.isspace):
            group_size = len(list(group))
            # if groups and is_space and group_size <= 2:
            #     prev_sp, prev_size = groups.pop(-1)
            #     groups.append((prev_sp, group_size + prev_size))
            # else:
            groups.append((is_space, group_size))
        return groups

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
                        # In Python 3.12, should be able to detect fstrings better
                        if (
                            token_list[0].type in (STRING, NAME)
                            and "f'" not in token_list[0].string
                        ):
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
                                (
                                    (iskeyword(tok_str) or cur_token.type == NAME)
                                    and old.type == NAME
                                )
                                and cur_line
                                and not cur_line[-1].isspace()
                            ):
                                tok_str = " " + tok_str
                    old = cur_token
                    space -= len(tok_str)
                    cur_line += tok_str
                carry_over = space
        if len(token_list) > 0:
            cur_line = cur_line + "\\\n"
        if cur_line:
            new_lines.append(cur_line)
    return "".join(new_lines)
