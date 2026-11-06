#include <klib.h>
#include "identity.h"

int main(void) {
  /* 个人标识固定；虚拟机IP由构建时生成的 identity.h 提供。 */
  printf("hello xiangshan, I am xvkongkabishourushishuo, IP address: %s\n", KKS_IP_ADDRESS);
  return 0;
}
