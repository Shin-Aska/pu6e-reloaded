// --------------------------------------------------
// a dictionary
// --------------------------------------------------

#define DICT_SIZE 10000

typedef struct dict_entry
{
  unsigned char root;
  int codeword;
} dict_entry_t;

static dict_entry_t dict[DICT_SIZE];
static int contains;

void dict_init() {
  contains = 0x102;
}

void dict_add(unsigned char root, int codeword) {
  dict[contains].root = root;
  dict[contains].codeword = codeword;
  contains++;
}

unsigned char dict_get_root(int codeword) {
  return (dict[codeword].root);
}

int dict_get_codeword(int codeword) {
  return (dict[codeword].codeword);
}
