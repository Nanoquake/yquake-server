#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>

#define PY_PORT 65432

//#ifndef __PYSOCK_H__
//#define __PYSOCK_H__

int get_socket_fd();

struct sockaddr_in address;
//extern int pysock;
int pysock;
struct sockaddr_in serv_addr;

//#endif
