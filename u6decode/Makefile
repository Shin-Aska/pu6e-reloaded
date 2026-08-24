CC=gcc
AR=ar
CFLAGS=-O2

LOBJS=lzw.o dict.o stack.o
LIB=libu6lzw.a

BOBJS=decode.o
BIN=lzwdec
LIBS=-lu6lzw

all: $(BIN) $(LIB)

$(LIB): $(LOBJS)
	$(AR) rcs $@ $(LOBJS)

$(BIN): $(LIB) $(BOBJS)
	$(CC) -o $@ $(BOBJS) -L. $(LIBS)

%.o: %.c
	$(CC) $(CFLAGS) -o $@ -c $<

clean:
	rm -f $(BOBJS) $(LIB) $(LOBJS) $(BIN)
