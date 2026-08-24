#include "lzw.h"

// ----------------------------------------------------------
// called if the program is run with 1 command line parameter
// display uncompressed file size
// ----------------------------------------------------------
static void one_argument(char *file_name) {
   FILE *compressed_file;
   long uncompressed_size;

   compressed_file = fopen(file_name,"rb");
   if (compressed_file==NULL) {
      printf("Couldn't open the file.\n");
   }
   else {
      uncompressed_size = get_uncompressed_size(compressed_file);
      if (uncompressed_size==(-1)) {
         printf("The input file is not a valid LZW-compressed file.\n");
      }
      else {
         printf("The uncompressed file '%s' would be %d bytes long.\n",file_name,get_uncompressed_size(compressed_file));
         fclose(compressed_file);
      }
   }
}


// -----------------------------------------------------------
// called if the program is run with 2 command line parameters
// decompress arg1 into arg2
// -----------------------------------------------------------
static void two_arguments(char *source_file_name, char *destination_file_name)
{
   FILE *source;
   FILE *destination;

   if (strcmp (source_file_name, destination_file_name) == 0)
   {
      printf("Source and destination must not be identical.\n");
   }
   else
   {
      if (!(source=fopen(source_file_name,"rb"))||!(destination=fopen(destination_file_name,"wb")))
      {
         printf("Couldn't open '%s' or '%s' or both.\n.", source_file_name, destination_file_name);
      }
      else
      {
         if (is_valid_lzw_file(source)) { lzw_decompress_file(source,destination); }
         else { printf("The input file is not a valid LZW-compressed file.\n"); }
      }
   }
}


main (int argc, char *argv[]) {

// 0 args => print help message
// 1 arg ==> display uncompressed file size, but don't decompress
// 2 args => decompress arg1 into arg2

 switch (argc)
 {
 case 1:
     printf("Usage:\n");
     printf("0 parameters - this message.\n");
     printf("1 parameter  - display uncompressed size.\n");
     printf("2 parameters - extract arg1 into arg2.\n");
     break;
 case 2:
     one_argument(argv[1]);
     break;
 case 3:
     two_arguments(argv[1],argv[2]);
     break;
 default:
     printf("Too many command line parameters.\n");
 }

}
