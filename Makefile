TARGETS := bfloo
CXXFLAGS := -W -Wall -g
LDLIBS := -llightning
PYTHON := python

all: $(TARGETS)

check: bfloo
	@echo All runs below should print "Hello World!" to the console.
	./bfloo examples/hello.bf
	$(PYTHON) ./bfo.py examples/hello.bf
	$(PYTHON) ./bf.py examples/hello.bf

profile: bfloo
	time (echo 50 | ./bfloo examples/primes.bf)
	time (echo 50 | $(PYTHON) ./bfo.py examples/primes.bf)
	time (echo 50 | $(PYTHON) ./bf.py examples/primes.bf)

clean:
	rm -f $(TARGETS)
