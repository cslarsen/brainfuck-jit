Brainfuck-JIT
=============

Contains code from the presentation "How to make a simple virtual machine". The
The accompanying slides are available at
https://speakerdeck.com/csl/how-to-make-a-simple-virtual-machine

In the talk, I showed how to build several Brainfuck virtual machines.  The aim
is to teach virtual machine interpretation and compilation topics. For
instance, in the first interpreter, we need a runtime stack to manage loops. In
the JIT-compiler, we only use a stack during compile-time: The finished code
will use addresses for jumps.

Requirements and build instructions
-----------------------------------

The pure Python interpreter should work on both Python 2 and 3. The
JIT-to-CPython bytecode version requires the `byteplay` module, available
through pip (but only for Python 2.x):

    $ pip install byteplay

Finally, the C++ JIT-compiler to machine code requires GNU Lightning. I had
trouble compiling this on Linux, and I had to disable shared libraries:

    $ # download GNU Lightning source code
    $ ./configure --disable-shared
    $ make -j
    $ make check
    $ make install

To buil the C++ Brainfuck VM, you should now simply do

    $ g++ -W -Wall -g bfloo.cpp -obfloo.cpp -llightning

For your convenience, you can also probably just do:

    $ make -j

If you compiled with debug symbols, as shown above, you can disassemble the
JIT-ed code with gdb or lldb:

    $ gdb ./bfloo
    (gdb) break Machine::run
    (gdb) run examples/hello.bf
    ...
    (gdb) print *this
    { ... { code = 0xDEADBEEF... }}
    (gdb) x/i 0xDEADBEEF...

If you don't like AT&T assembly syntax, do

    (gdb) set disassembly-flavor intel

Checking the VMs
----------------

Type `make check` to quickly see if the VMs work.

Running examples
----------------

The Brainfuck examples were taken from the net. You can view their sources to
see who made them.

Most programs take the program name as the first option. The pure Python
interpreter:

    $ python bf.py examples/hello.bf

To-Python bytecode JIT:

    $ python bfc.py examples/hello.bf

Same, but with some optimizations:

    $ python bfo.py examples/hello.bf

The Python versions take some options:

    -u8   Use 8-bit memory cells
    -u16  Use 16-bit memory cells
    -u32  Use 32-bit memory cells

Some programs, in particular `bottles.bf`, require 8-bit cells.  You can also
use the option `-b` to buffer output (i.e., not run `flush()` for every printed
item).

The C++ VM only takes the Brainfuck files as input:

    $ ./bfloo examples/hello.bf

Note that some of the optimizations in the code may be incorrect, and thus some
demos may not work for the different VMs.

Also, if you like this, be sure to check out my blog post on how to write
simple stack machines: https://csl.name/post/vm/

Finally, there are a lot of really cool Brainfuck interpreters, optimizers and
JIT-ers on the net.

Running Brainfuck in Brainfuck
------------------------------

The file `examples/brainfuck.bf` contains a Brainfuck interpreter written in
Brainfuck.  You need to send both the program code and user input to standard
input, separated with a `!`, for example:

    $ echo `cat examples/primes.bf`'!40' | ./bfloo examples/brainfuck.bf

Comparing the various VMs
-------------------------

Type `make profile` to time the running time of the different VMs on some
particular Brainfuck programs.

Author and license
------------------
Copyright (C) 2015 Christian Stigen Larsen  

Distributed under the LGPL v2.1 or later. You are allowed to change the license
on a particular copy to the LGPL 3.0, the GPL 2.0 or GPL 3.0.
