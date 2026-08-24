// =============================================================
// This program decompresses Ultima6-style LZW-compressed files
// =============================================================

#include <stdio.h>
#include "lzw.h"

static long read4(FILE *f)
{
    unsigned char b0, b1, b2, b3;
    b0 = fgetc(f);
    b1 = fgetc(f);
    b2 = fgetc(f);
    b3 = fgetc(f);
    return (b0 + (b1<<8) + (b2<<16) + (b3<<24));
}

static long get_filesize(FILE *input_file)
{
   long file_length;
   fseek(input_file, 0, SEEK_END);
   file_length = ftell(input_file);
   fseek(input_file, 0, SEEK_SET);
   return(file_length);
}

/* buf must be at least 6 characters long */
int is_valid_lzw_buffer(char *buf, int length) {
    // file must contain 4-byte size header and space for the 9-bit value 0x100
    // the last byte of the size header must be 0 (U6's files aren't *that* big)
	if (length < 6) return 0;
	if (buf[3] != 0) return 0;
    // the 9 bits after the size header must be 0x100
    if ((buf[4] != 0) || ((buf[5] & 1) != 1)) return 0;
	return 1;
}

// this function only checks a few *necessary* conditions
// returns "0" if the file doesn't satisfy these conditions
// return "1" otherwise
int is_valid_lzw_file(FILE *input_file)
{
	char buf[6];
    // if (get_filesize(input_file) < 6) { return(0); }
    // the last byte of the size header must be 0 (U6's files aren't *that* big)
    if (fread(buf, 6, 1, input_file) != 1) return 0;
	fseek(input_file, 0, SEEK_SET);
	if (!is_valid_lzw_buffer(buf, 6)) return 0;
    return 1;
}

/* Must be unsigned char rather than char; otherwise nasty bit
 * problems crop up */
int get_uncompressed_size_buffer(unsigned char *buf, int length)
{
   if (length < 4) return -1;
   return (buf[0] | (buf[1]<<8) | (buf[2]<<16) | (buf[3]<<24));
}

int get_uncompressed_size(FILE *input_file)
{
	int len;
	char buf[4];
	fseek(input_file, 0, SEEK_SET);
	fread(buf, 4, 1, input_file);
	len = get_uncompressed_size_buffer(buf, 4);
	fseek(input_file, 0, SEEK_SET);
	return len;
}

// ----------------------------------------------
// Read the next code word from the source buffer
// ----------------------------------------------
static int get_next_codeword (long *bits_read, unsigned char *source, int codeword_size)
{
   unsigned char b0,b1,b2;
   int codeword;

   b0 = source[*bits_read/8];
   b1 = source[*bits_read/8+1];
   b2 = source[*bits_read/8+2];

   codeword = ((b2 << 16) + (b1 << 8) + b0);
   codeword = codeword >> (*bits_read % 8);
   switch (codeword_size)
   {
    case 0x9:
        codeword = codeword & 0x1ff;
        break;
    case 0xa:
        codeword = codeword & 0x3ff;
        break;
    case 0xb:
        codeword = codeword & 0x7ff;
        break;
    case 0xc:
        codeword = codeword & 0xfff;
        break;
    default:
        printf("Error: weird codeword size!\n");
        break;
   }
   *bits_read += codeword_size;

   return (codeword);
}

static void output_root(unsigned char root, unsigned char *destination, long *position)
{
   destination[*position] = root;
   (*position)++;
}

static void get_string(int codeword)
{
   unsigned char root;
   int current_codeword;

   current_codeword = codeword;
   stack_init();
   while (current_codeword > 0xff)
   {
      root = dict_get_root(current_codeword);
      current_codeword = dict_get_codeword(current_codeword);
      stack_push(root);
   }

   // push the root at the leaf
   stack_push((unsigned char)current_codeword);
}

// -----------------------------------------------------------------------------
// LZW-decompress from buffer to buffer.
// The parameters "source_length" and "destination_length" are currently unused.
// They might be used to prevent reading/writing outside the buffers.
// -----------------------------------------------------------------------------
void lzw_decompress_buffer(unsigned char *source, long source_length, unsigned char *destination, long destination_length)
{
   const int max_codeword_length = 12;

   int end_marker_reached = 0;
   int codeword_size = 9;
   long bits_read = 0;
   int next_free_codeword = 0x102;
   int dictionary_size = 0x200;

   long bytes_written = 0;

   int cW;
   int pW = 0;
   unsigned char C;

   while (! end_marker_reached)
   {
      cW = get_next_codeword(&bits_read, source, codeword_size);
      switch (cW)
      {
      // re-init the dictionary
      case 0x100:
          codeword_size = 9;
          next_free_codeword = 0x102;
          dictionary_size = 0x200;
          dict_init();
          cW = get_next_codeword(&bits_read, source, codeword_size);
          output_root((unsigned char)cW, destination, &bytes_written);
          break;
      // end of compressed file has been reached
      case 0x101:
          end_marker_reached = 1;
          break;
      // (cW <> 0x100) && (cW <> 0x101)
      default:
          if (cW < next_free_codeword)  // codeword is already in the dictionary
          {
             // create the string associated with cW (on the stack)
             get_string(cW);
             C = stack_top();
             // output the string represented by cW
             while (!stack_is_empty())
             {
                output_root(stack_pop(), destination, &bytes_written);
             }
             // add pW+C to the dictionary
             dict_add(C,pW);

             next_free_codeword++;
             if (next_free_codeword >= dictionary_size)
             {
                if (codeword_size < max_codeword_length)
                {
                   codeword_size += 1;
                   dictionary_size *= 2;
                }
             }
          }
          else  // codeword is not yet defined
          {
             // create the string associated with pW (on the stack)
             get_string(pW);
             C = stack_top();
             // output the string represented by pW
             while (!stack_is_empty())
             {
                output_root(stack_pop(), destination, &bytes_written);
             }
             // output the char C
             output_root(C, destination, &bytes_written);
             // the new dictionary entry must correspond to cW
             // if it doesn't, something is wrong with the lzw-compressed data.
             if (cW != next_free_codeword)
             {
                printf("cW != next_free_codeword!\n");
                exit(-1);
             }
             // add pW+C to the dictionary
             dict_add(C,pW);

             next_free_codeword++;
             if (next_free_codeword >= dictionary_size)
             {
                if (codeword_size < max_codeword_length)
                {
                   codeword_size += 1;
                   dictionary_size *= 2;
                }
             }
          };
          break;
      }
      // shift roles - the current cW becomes the new pW
      pW = cW;
   }
}

// ------------------------------------------------
// from file to file
// assume input_file is a valid LZW-compressed file
// ------------------------------------------------
void lzw_decompress_file(FILE *input_file, FILE* output_file)
{
   unsigned char *source_buffer;
   unsigned char *destination_buffer;
   long source_buffer_size;
   long destination_buffer_size;

  // determine the buffer sizes
  source_buffer_size = get_filesize(input_file)-4;
  destination_buffer_size = get_uncompressed_size(input_file);

  // create the buffers
  source_buffer = (unsigned char *)malloc(source_buffer_size);
  destination_buffer = (unsigned char *)malloc(destination_buffer_size);

  // read the input file into the source buffer
  fseek(input_file, 4, SEEK_SET);
  fread(source_buffer, 1, source_buffer_size, input_file);

  // decompress the input file
  lzw_decompress_buffer(source_buffer,source_buffer_size,destination_buffer,destination_buffer_size);

  // write the destination buffer to the output file
  fwrite(destination_buffer, 1, destination_buffer_size, output_file);
  fflush(output_file);

  // destroy the buffers
  free(source_buffer);
  free(destination_buffer);
}
