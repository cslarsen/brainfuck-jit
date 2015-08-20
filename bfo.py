#!/usr/bin/env python

"""Brainf**k JIT-compiler that produces CPython bytecode.
You need the byteplay module to run this.

Note that this VM may not reliably run some example programs. This is probably
because of bugs.  Also, it doesn't implement extended jumps, so some programs
with long jumps will not work with this one.  In particular, it doesn't seem to
run hanoi.bf correctly.

Copyright (C) 2015 Christian Stigen Larsen

Distributed under the LGPL v2.1 or later. You are allowed to change the license
on a particular copy to the LGPL 3.0, the GPL 2.0 or GPL 3.0.
"""

from collections import deque
import byteplay as bp
import os
import sys

def optimize_source(source, verbose=False):
    if verbose:
        sys.stderr.write("optimizing ...")
        sys.stderr.flush()

    # Remove unknown operations
    source = filter(lambda x: x in "+-<>.,[]", source)

    # Contract sequences of same operators
    out, prev, count = [], None, 0
    for op in source:
        if (op in "[]") or (op != prev):
            if count > 0:
                out.append((prev, count))
            prev, count = op, 1
        else:
            count += 1
    out.append((prev, count))

    if verbose:
        sys.stderr.write("\n")
        sys.stderr.write("optimized from %d to %d instructions\n" % (len(source), len(out)))

    if len(out) > 4096:
        # Find largest jump length
        maxlen = 0
        s = deque()
        for pos, (op, _) in enumerate(out):
            if op == "[":
                s.append(pos)
            elif op == "]":
                maxlen = max(maxlen, pos-s.pop())

        if maxlen > 4096:
            sys.stderr.write(("warning: found jump larger than %d positions\n" %
                maxlen))
            sys.stderr.write("          (that will probably not work with byteplay)\n")

    return out

def compile(source, memsize=300000, flush=True, modulus=None, verbose=False):
    # Bytecode
    c = []

    # Keep track of jump labels
    labels = []
    labelpos = {}


    # import sys
    c.append((bp.LOAD_CONST, -1))
    c.append((bp.LOAD_CONST, None))
    c.append((bp.IMPORT_NAME, "sys"))
    c.append((bp.STORE_FAST, "sys"))

    # memory = [0]*memsize
    c.append((bp.LOAD_CONST, 0))
    c.append((bp.BUILD_LIST, 1))
    c.append((bp.LOAD_CONST, memsize))
    c.append((bp.BINARY_MULTIPLY, None))
    c.append((bp.STORE_FAST, "memory"))

    # ptr = 0
    c.append((bp.LOAD_CONST, 0))
    c.append((bp.STORE_FAST, "ptr"))

    def add(value):
        if modulus is None:
            c.append((bp.LOAD_FAST, "memory"))
            c.append((bp.LOAD_FAST, "ptr"))
            c.append((bp.DUP_TOPX, 2))
            c.append((bp.BINARY_SUBSCR, None))
            c.append((bp.LOAD_CONST, value))
            c.append((bp.INPLACE_ADD, None))
            c.append((bp.ROT_THREE, None))
            c.append((bp.STORE_SUBSCR, None))
        else:
            c.append((bp.LOAD_FAST, "memory"))
            c.append((bp.LOAD_FAST, "ptr"))
            c.append((bp.BINARY_SUBSCR, None))
            c.append((bp.LOAD_CONST, value))
            c.append((bp.BINARY_ADD, None))
            c.append((bp.LOAD_CONST, modulus))
            c.append((bp.BINARY_MODULO, None))
            c.append((bp.LOAD_FAST, "memory"))
            c.append((bp.LOAD_FAST, "ptr"))
            c.append((bp.STORE_SUBSCR, None))

    def dot(count):
        # Prepare call to sys.stdout.write(chr(...))
        c.append((bp.LOAD_GLOBAL, "sys"))
        c.append((bp.LOAD_ATTR, "stdout"))
        c.append((bp.LOAD_ATTR, "write"))
        c.append((bp.LOAD_GLOBAL, "chr"))

        # Get value
        c.append((bp.LOAD_FAST, "memory"))
        c.append((bp.LOAD_FAST, "ptr"))
        c.append((bp.BINARY_SUBSCR, None))

        # Call chr
        c.append((bp.CALL_FUNCTION, 1))

        if count > 1:
            c.append((bp.LOAD_CONST, count))
            c.append((bp.BINARY_MULTIPLY, None))

        # Call sys.stdout.write and drop its return value
        c.append((bp.CALL_FUNCTION, 1))
        c.append((bp.POP_TOP, None))

        if flush:
            c.append((bp.LOAD_GLOBAL, "sys"))
            c.append((bp.LOAD_ATTR, "stdout"))
            c.append((bp.LOAD_ATTR, "flush"))
            c.append((bp.CALL_FUNCTION, 0))
            c.append((bp.POP_TOP, None))

    def comma(count):
        c.append((bp.LOAD_GLOBAL, "ord"))
        c.append((bp.LOAD_FAST, "sys"))
        c.append((bp.LOAD_ATTR, "stdin"))
        c.append((bp.LOAD_ATTR, "read"))
        c.append((bp.LOAD_CONST, count))
        c.append((bp.CALL_FUNCTION, 1))
        c.append((bp.CALL_FUNCTION, 1))
        c.append((bp.LOAD_FAST, "memory"))
        c.append((bp.LOAD_FAST, "ptr"))
        c.append((bp.STORE_SUBSCR, None))

    def move(amount):
        c.append((bp.LOAD_FAST, "ptr"))
        c.append((bp.LOAD_CONST, amount))
        c.append((bp.INPLACE_ADD, None))
        c.append((bp.STORE_FAST, "ptr"))

    def start_loop(label):
        c.append((label, None))
        c.append((bp.LOAD_FAST, "memory"))
        c.append((bp.LOAD_FAST, "ptr"))
        c.append((bp.BINARY_SUBSCR, None))
        c.append((bp.LOAD_CONST, 0))
        c.append((bp.COMPARE_OP, "=="))

        # We don't know the label of the end-of-loop position, so store a
        # temporary marker and get back to it later
        c.append((bp.POP_JUMP_IF_TRUE, None))
        labelpos[label] = len(c)-1

    def end_loop(startlabel):
        endlabel = bp.Label()

        # Update goto end-of-loop label
        start = labelpos[startlabel]
        c[start] = (bp.POP_JUMP_IF_TRUE, endlabel)

        c.append((endlabel, None))
        c.append((bp.LOAD_FAST, "memory"))
        c.append((bp.LOAD_FAST, "ptr"))
        c.append((bp.BINARY_SUBSCR, None))
        c.append((bp.LOAD_CONST, 0))
        c.append((bp.COMPARE_OP, "=="))
        c.append((bp.POP_JUMP_IF_FALSE, startlabel))

    # Translate Brainfuck to Python bytecode
    for (op, count) in optimize_source(source, verbose=verbose):
        if op == ">":
            move(count)
        elif op == "<":
            move(-count)
        elif op == "+":
            add(count)
        elif op == "-":
            add(-count)
        elif op == ".":
            dot(count)
        elif op == ",":
            comma(count)
        elif op == "[":
            labels.append(bp.Label())
            start_loop(labels[-1])
        elif op == "]":
            end_loop(labels.pop())
        else:
            print("Unknown operator: %s" % op)
            sys.exit(1)
            continue

    # return None
    c.append((bp.LOAD_CONST, None))
    c.append((bp.RETURN_VALUE, None))
    return c

def to_code(bytecode, name = "", docstring="", filename=""):
    arglist = ()
    freevars = []
    varargs = False
    varkwargs = False
    newlocals = True
    firstlineno = 1

    codeobj = bp.Code(bytecode, freevars=freevars, args=arglist,
            varargs=varargs, varkwargs=varkwargs, newlocals=newlocals,
            name=name, filename=filename, firstlineno=firstlineno,
            docstring=docstring)

    return codeobj

def make_function(codeobj):
    func = lambda: None
    func.__doc__ = codeobj.docstring
    func.__name__ == codeobj.name
    func.func_code = bp.Code.to_code(codeobj)
    return func

if __name__ == "__main__":
    export = False
    flush = True
    modulus = None
    verbose = False

    for arg in sys.argv[1:]:
        if arg == "-e":
            export = True
        elif arg == "-b":
            flush = False
        elif arg == "-u8":
            modulus = 2**8
        elif arg == "-u16":
            modulus = 2**16
        elif arg == "-u32":
            modulus = 2**32
        elif arg == "-v":
            verbose = True

    for filename in sys.argv[1:]:
        if filename[0] == "-":
            continue
        with open(filename, "rt") as file:
            name = os.path.splitext(os.path.basename(filename))[0]

            source = file.read()
            compiled = compile(list(source), flush=flush, modulus=modulus,
                    verbose=verbose)
            program = make_function(to_code(compiled, name=name))

            if not export:
                program()
            else:
                import marshal
                s = marshal.dumps(program.func_code)
                with open(name + ".marshalled", "wb") as f:
                    f.write(s)
