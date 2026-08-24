// --------------------------------------------------
// a simple implementation of an equally simple stack
// --------------------------------------------------

#define STACK_SIZE 10000

static unsigned char stack[STACK_SIZE];
static int contains;

void stack_init() {
  contains = 0;
}

int stack_is_empty() {
  return (contains==0);
}

int stack_is_full() {
  return (contains==STACK_SIZE);
}

void stack_push(unsigned char element) {
  if (!stack_is_full()) {
	 stack[contains] = element;
	 contains++;
  }
}

unsigned char stack_pop() {
  unsigned char element;

  if (!stack_is_empty()) {
	 element = stack[contains-1];
	 contains--;
  }
  else {
	 element = 0;
  }
  return(element);
}

unsigned char stack_top()
{
  if (!stack_is_empty()) {
	 return(stack[contains-1]);
  }
  return 0;
}
