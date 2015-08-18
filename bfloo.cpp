/*
 * Brainf**k JIT-compiler that produces machine code.
 * Requires GNU Lightning.
 *
 * Copyright (C) 2015 Christian Stigen Larsen
 *
 * Distributed under the LGPL v2.1 or later. You are allowed to change the
 * license on a particular copy to the LGPL 3.0, the GPL 2.0 or GPL 3.0.
 */

#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include <stack>
#include <vector>

extern "C" {
#include <lightning.h>
}

typedef void (*vfptr)(void);

static jit_state_t *_jit;
static bool silent = true;

struct Loop {
  jit_node_t *body;
  jit_node_t *end;
};

struct Oper {
  char code;
  int count;

  Oper(const char code_, const int count_ = 1):
    code(code_), count(count_)
  {
  }
};

// Contract many <>+- to Op('+', 123) etc.
std::vector<Oper> optimize(FILE* f)
{
  std::vector<Oper> ops;

  for ( int c=0; c != EOF; c = fgetc(f) ) {
    // skip unknown ops
    if ( !strchr("<>+-.,[]", c) )
      continue;

    Oper op(c, 1);
    if ( strchr("+-<>", c) ) {
      int n = fgetc(f);
      while ( n != EOF && n == c ) {
        ++op.count;
        n = fgetc(f);
      }
      ungetc(n, f);
    }

    ops.push_back(op);
  }

  // Special [-] ==> set current cell to zero
  for ( size_t n=0; n+2<ops.size(); ++n ) {
    Oper a = ops[n];
    Oper b = ops[n+1];
    Oper c = ops[n+2];
    if ( a.code=='[' && b.code=='-' && b.count==1 && c.code==']' ) {
      ops.erase(ops.begin()+n, ops.begin()+n+3);
      ops.insert(ops.begin()+n, Oper('z', 0));
      continue;
    }
  }

  return ops;
}

jit_pointer_t compile(const std::vector<Oper>& ops, jit_word_t *memory, const bool flush = true)
{
  jit_prolog();
  jit_movi(JIT_V0, reinterpret_cast<jit_word_t>(memory));
  jit_movi(JIT_V1, 0);

  std::stack<Loop> loops;

  jit_node_t* start = jit_note(__FILE__, __LINE__);

  for ( size_t n=0; n<ops.size(); ++n ) {
    switch ( ops[n].code ) {
      case '<':
        jit_str(JIT_V0, JIT_V1);
        jit_subi(JIT_V0, JIT_V0, ops[n].count * sizeof(jit_word_t));
        jit_ldr(JIT_V1, JIT_V0);
        break;

      case '>':
        jit_str(JIT_V0, JIT_V1);
        jit_addi(JIT_V0, JIT_V0, ops[n].count * sizeof(jit_word_t));
        jit_ldr(JIT_V1, JIT_V0);
        break;

      case 'z':
        jit_movi(JIT_V1, 0);
        break;

      case '+':
        jit_addi(JIT_V1, JIT_V1, ops[n].count);
        break;

      case '-':
        jit_subi(JIT_V1, JIT_V1, ops[n].count);
        break;

      case '.':
        jit_prepare();
        jit_pushargr(JIT_V1);
        jit_finishi(reinterpret_cast<jit_pointer_t>(putchar));

        if ( flush ) {
          jit_prepare();
          jit_pushargi(reinterpret_cast<jit_word_t>(stdout));
          jit_finishi(reinterpret_cast<jit_pointer_t>(fflush));
        }
        break;

      case ',':
        jit_prepare();
        jit_finishi(reinterpret_cast<jit_pointer_t>(getchar));
        jit_retval(JIT_V1);
        break;

      case '[': {
        Loop loop;
        loop.end = jit_forward();
        jit_node_t *j = jit_beqi(JIT_V1, 0);
        jit_patch_at(j, loop.end);
        loop.body = jit_label();
        loops.push(loop);
      } break;

      case ']': {
        Loop loop = loops.top();
        jit_node_t *j = jit_bnei(JIT_V1, 0);
        jit_patch_at(j, loop.body);
        jit_link(loop.end);
        loops.pop();
        break;
      }
      default:
        break;
    }
  }

  jit_node_t* stop = jit_note(__FILE__, __LINE__);

  jit_ret();
  jit_epilog();
  jit_pointer_t r = jit_emit();

  if ( !silent ) {
    fprintf(stderr, "compiled to %zu bytes\n", (char*)jit_address(stop) -
        (char*)jit_address(start));
  }

  return r;
}

struct Machine {
  jit_word_t *memory;
  vfptr program;

  Machine(const size_t memsize = 100000)
    : memory(static_cast<jit_word_t*>(malloc(sizeof(jit_word_t)*memsize))),
      program(NULL)
  {
    memset(memory, 0, sizeof(jit_word_t)*memsize);
  }

  void compile(FILE* f)
  {
    std::vector<Oper> ops = optimize(f);
    program = reinterpret_cast<vfptr>(::compile(ops, memory));
  }

  ~Machine()
  {
    free(memory);
  }

  void run()
  {
    program();
  }
};

int main(int argc, char *argv[])
{
  init_jit(argv[0]);
  _jit = jit_new_state();

  for ( int n=1; n<argc; ++n )
    if ( !strcmp(argv[n], "-v") ) {
      silent = false;
    }

  for ( int n=1; n<argc; ++n ) {
    if ( argv[n][0] == '-' && argv[n][1] != '\0' )
      continue;

    FILE *f = !strcmp(argv[n], "-")? stdin : fopen(argv[n], "rt");

    if ( !f ) {
      perror(argv[n]);
      return 1;
    } else {
      Machine p;
      p.compile(f);
      fclose(f);
      p.run();
    }
  }

  jit_destroy_state();
  finish_jit();
  return 0;
}
