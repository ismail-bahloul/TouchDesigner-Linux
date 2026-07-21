CC       := gcc
MINGW_CC := x86_64-w64-mingw32-gcc

CFLAGS    := -Wall -Wextra -O2 -std=c11
LDFLAGS   := -ldl

MINGW_CFLAGS := -Wall -Wextra -O2 -std=c11

.PHONY: all clean

all: cuda_daemon nvcuda.dll

cuda_daemon: cuda_daemon.c
	$(CC) $(CFLAGS) -o $@ $< $(LDFLAGS)

nvcuda.dll: nvcuda_daemon_pe.c
	$(MINGW_CC) $(MINGW_CFLAGS) -shared -o $@ $^ -lkernel32

clean:
	rm -f cuda_daemon nvcuda.dll
