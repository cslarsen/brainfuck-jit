#!/usr/bin/env python

"""Brainf**k interpreter

Copyright (C) 2015 Christian Stigen Larsen

Distributed under the LGPL v2.1 or later. You are allowed to change the license
on a particular copy to the LGPL 3.0, the GPL 2.0 or GPL 3.0.
"""

import sys
from collections import deque

class Machine(object):
    def __init__(self, code, memory=100000, modulus=None):
        # Code and pointer (program counter)
        self.code = code
        self.cptr = 0

        # Memory and pointer
        self.memory = [0]*memory
        self.mptr = 0

        # Other stuff
        self.stack = deque([])
        self.skip_memo = {}
        self.mod = modulus

    @property
    def byte(self):
        """Returns value of current memory cell."""
        return self.memory[self.mptr]

    @byte.setter
    def byte(self, value):
        """Sets value of current memory cell."""
        self.memory[self.mptr] = value

    def next(self):
        """Returns next instruction and increments program counter."""
        try:
            i = self.code[self.cptr]
            self.cptr += 1
            return i
        except IndexError:
            raise StopIteration()

    def dispatch(self, i):
        """Executes one instruction."""
        if i == ">":
            self.mptr += 1
        elif i == "<":
            self.mptr -= 1
        elif i == "+":
            if not self.mod:
                self.byte += 1
            else:
                self.byte = (self.byte + 1) % self.mod
        elif i == "-":
            if not self.mod:
                self.byte -= 1
            else:
                self.byte = (self.byte - 1) % self.mod
        elif i == ".":
            sys.stdout.write(chr(self.byte))
            sys.stdout.flush()
        elif i == ",":
            self.byte = ord(sys.stdin.read(1))
        elif i == "[":
            if self.byte != 0:
                self.stack.append(self.cptr-1)
            else:
                self.skip_block()
        elif i == "]":
            ret = self.stack.pop()
            if self.byte != 0:
                self.cptr = ret
        else:
            # Ignore unknown instructions
            pass

    def skip_block(self):
        """Skips to the corresponding closing bracket."""
        # Memoize
        if self.cptr in self.skip_memo:
            self.cptr = self.skip_memo[self.cptr]
            return
        else:
            cptr = self.cptr

        count = 1
        while count > 0:
            i = self.next()
            if i == "[":
                count += 1
            elif i == "]":
                count -= 1

        # Memoize
        self.skip_memo[cptr] = self.cptr

    def step(self):
        """Runs one instruction. Can be called many times.

        Raises StopIteration when program is complete.
        """
        self.dispatch(self.next())

    def run(self):
        """Runs program until it ends."""
        try:
            while True:
                self.step()
        except StopIteration:
            pass


if __name__ == "__main__":
    modulus = None
    for a in sys.argv[1:]:
        if a == "-u8":
            modulus = 2**8
        elif a == "-u16":
            modulus = 2**16
        elif a == "-u32":
            modulus = 2**32

    for f in sys.argv[1:]:
        if f[0] == "-":
            continue
        with open(f, "rb") as file:
            m = Machine(list(file.read()), modulus=modulus)
            m.run()
