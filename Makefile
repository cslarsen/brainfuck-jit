TARGETS := bfloo
CXXFLAGS := -W -Wall -g
LDFLAGS := -llightning

all: $(TARGETS)

check: bfloo
	@echo All runs below should print "Hello World!" to the console.
	./bfloo examples/hello.bf
	./bfo.py examples/hello.bf
	./bf.py examples/hello.bf

profile: bfloo
	time (echo 50 | ./bfloo examples/primes.bf)
	time (echo 50 | ./bfo.py examples/primes.bf)
	time (echo 50 | ./bf.py examples/primes.bf)

clean:
	rm -f $(TARGETS)
