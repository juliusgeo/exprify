from exprify import reflow, transpile_script_source
import argparse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=str, help="Source code to exprify")
    parser.add_argument("-o", "--outline", type=str, help="increase output verbosity")
    parser.add_argument("-t", "--tolerance", type=int, help="increase output verbosity")
    args = parser.parse_args()
    script = open(args.source).read()
    if args.outline:
        outline = open(args.outline).read()
        if args.tolerance:
            reflowed_script = reflow(script, outline, args.tolerance)
        else:
            reflowed_script = reflow(script, outline)
        print(reflowed_script)
    else:
        print(transpile_script_source(script))
