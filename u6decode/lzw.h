#ifndef __LZW_H__
#define __LZW_H__

#include <stdio.h>
#include <stdlib.h>

/* stack */
void stack_init(void);
int stack_is_empty(void);
int stack_is_full(void);
void stack_push(unsigned char element);
unsigned char stack_pop(void);
unsigned char stack_top(void);

/* dict */
void dict_init(void);
void dict_add(unsigned char root, int codeword);
unsigned char dict_get_root(int codeword);
int dict_get_codeword(int codeword);

/* lzw */
int is_valid_lzw_buffer(char *buf, int length);
int is_valid_lzw_file(FILE *input_file);
int get_uncompressed_size_buffer(unsigned char *buf, int length);
int get_uncompressed_size(FILE *input_file);
void lzw_decompress_buffer(unsigned char *source, long source_length, unsigned char *destination, long destination_length);
void lzw_decompress_file(FILE *input_file, FILE* output_file);

#endif
