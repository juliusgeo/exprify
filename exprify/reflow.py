from sys import version_info


from exprify import transpile_script_source
from itertools import groupby
from keyword import iskeyword
from tokenize import (
    NAME,
    STRING,
    NUMBER,
    tokenize,
    TokenInfo,
)
import tokenize as tk
import io
import python_minifier


FSTRING_STARTS = ("f'", 'f"')
BSTRING_STARTS = ("b'", 'b"')

TOLERANCE = 4
# Make sure that "\\" is at the end, because it has the smallest window
INVALID_SPLIT_CHARS = {"\\U": 8, "\\u": 4, "\\x": 2, "\\": 1}


# Fallback for Python < 3.12
def merge_fstring_literals(tokens):
    return tokens


if version_info >= (3, 12, 0):
    # In Python versions >= 3.12, f-strings are now tokenized differently
    # such that the expressions inside of braces are just normal OP, NAME, etc
    # tokens rather than the previous behavior which tokenized the entire f-string as one.
    # To keep the logic consistent in reflowing, we need to merge together all the tokens inside
    # an f-string.
    from tokenize import FSTRING_END

    def merge_fstring_literals(tokens):  # noqa: F811
        merged_tokens = []
        fstring_buffer = ""
        for tok in tokens:
            match tok.type:
                case tk.FSTRING_START:
                    fstring_buffer += tok.string
                case tk.FSTRING_END:
                    fstring_buffer += tok.string
                    merged_tok = TokenInfo(
                        **tok._asdict() | dict(string=fstring_buffer)
                    )
                    merged_tokens.append(merged_tok)
                    fstring_buffer = ""
                case _:
                    prefix = ""
                    if tok.type in (NAME, NUMBER):
                        prefix = " "
                    if fstring_buffer:
                        fstring_buffer += prefix + tok.string
                    else:
                        merged_tokens.append(tok)
        return merged_tokens

else:
    FSTRING_END = STRING


def poss_fstring_splits(ts, space, tolerance):
    # Generate possible splits that wouldn't break the f-string (not inside of an embedded expression).
    # The range start is clamped so it is at minimum 2 to prevent splitting before the f-string identifier
    poss_splits = []
    format_specifier = False
    for i in range(max(space - tolerance, 2), space + tolerance + 1):
        if ts[i] == ":":
            format_specifier = True
        if ts[:i].count("{") == ts[:i].count("}") and not format_specifier:
            format_specifier = False
            if split_escape_offset(ts, i) == 0:
                poss_splits.append((i, abs(space - i)))
    return poss_splits


def split_escape_offset(ts, splpt):
    for ch, window in INVALID_SPLIT_CHARS.items():
        if ch in ts[splpt - window - 2 :]:
            return window
    return 0


def split_mangles_escape(ts, splpt):
    # if we have an escaped char as the last one, we want to go past it
    # keep going until we find a place to split that doesn't break any escaped chars
    while (offset := split_escape_offset(ts, splpt)) != 0:
        splpt += offset
    return splpt


def partition_token(tok, space, tolerance):
    ts = tok.string
    splpt = ts.find(".") if tok.type == NAME else space
    splpt = split_mangles_escape(ts, splpt)
    septok = "" if tok.type == NAME else "'"
    left, right = ts[:splpt] + septok, septok + ts[splpt:]
    if splpt <= 2:
        left, right = ts, ""
    if ts.startswith(FSTRING_STARTS):
        poss_splits = poss_fstring_splits(ts, space, tolerance)
        if poss_splits:
            splpt, _ = min(poss_splits, key=lambda x: x[1])
            left, right = (ts[:splpt] + "'", "f'" + ts[splpt:])
        else:
            left, right = ts, ""
    if ts.startswith(BSTRING_STARTS):
        if splpt >= len(ts):
            left, right = ts, ""
        else:
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
    print(script)
    script = python_minifier.minify(
        script,
        rename_locals=True,
        rename_globals=True,
        hoist_literals=True,
        remove_annotations=True,
    )
    script = transpile_script_source(script)
    old, *token_list = list(tokenize(io.BytesIO(bytes(script, "utf-8")).readline))
    token_list = merge_fstring_literals(token_list)
    new_lines = "\n'';\\\n"

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
                        if token_list[0].type in (STRING, NAME, FSTRING_END):
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

                    tok_str = cur_token.string.strip()

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
        if token_list:
            cur_line = cur_line + "\\"
        if cur_line:
            new_lines += cur_line + "\n"

    return "".join(new_lines)
