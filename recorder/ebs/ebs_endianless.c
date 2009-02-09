/*
 * experimental hack
 * bushi at mizi dot com
 *
 * gcc -O2 -s -o ebs ebs_endianless.c -Wall
 * ./ebs > a.mp3
 * mplayer a.mp3
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <unistd.h>
#include <signal.h>
#include <errno.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/tcp.h>
#include <netinet/ip.h>
#include <arpa/inet.h>

#include "ebs.h"

#define SERVER_IP "219.240.12.254"
#define CTL_PORT 5056
#define DATA_PORT 5057
#define PING_INTERVAL (3)

#ifndef countof
#  define countof(x) (sizeof(x)/sizeof(x[0]))
#endif

static const unsigned char packet_0[288] = {
	PACKET_0
};

static const unsigned char packet_1[288] = {
	PACKET_1
};

static const unsigned char packet_2[288] = {
	PACKET_2
};

static const unsigned char packet_3[288] = {
	PACKET_3
};

static unsigned char req_tok1[4] = {0,};

struct context_s;

struct ebs_sock {
	int sockfd;
#define ST_ERROR (-1)
#define ST_IDLE (0)
#define ST_CTL_START (1)
#define ST_DATA_START (1)
#define ST_CTL_PREPARE_REQ (2)
#define ST_DATA_LOOP (2)
#define ST_CTL_MAKE_REQ_1 (3)
#define ST_CTL_MAKE_REQ_2 (4)
#define ST_CTL_MAKE_REQ_3 (5)
#define ST_CTL_LOOP (6)
#define ST_CTL_SEND_REQ (7)
	int state;
	int (*rx_handler)(struct ebs_sock *);
	struct context_s *cxt;
	void *priv;
};

typedef struct context_s {
#define CTL_SOCK 0
#define DATA_SOCK 1
	struct ebs_sock socks[2]; /* ctl1, ctl2, data */
	int (*recv_data)(struct ebs_sock *, unsigned short len);
	unsigned char *buf;
} context_t;

int make_sock(struct ebs_sock *sock, const char *ipaddr, int port)
{
	int sockfd;
	struct sockaddr_in servaddr;
	int ret;

	ret = socket(AF_INET, SOCK_STREAM, 0);
	if (ret < 0) {
		perror("socket()");
		return ret;
	}
	sockfd = ret;

	bzero(&servaddr, sizeof(servaddr));
	servaddr.sin_family = AF_INET;
	servaddr.sin_port = htons(port);

	ret = inet_pton(AF_INET, ipaddr, &servaddr.sin_addr);
	if (ret < 0) {
		perror("inet_pton()");
		close(sockfd);
		return ret;
	}
	if (ret == 0) {
		fprintf(stderr, "invalid address\n");
		close(sockfd);
		return -1;
	}

	ret = connect(sockfd, (struct sockaddr *)&servaddr, sizeof(servaddr));
	if (ret < 0) {
		perror("connect()");
		close(sockfd);
		return ret;
	}

	sock->sockfd = sockfd;	

	return 0;
}

void destroy_context(context_t *cxt)
{
	int i;
	struct ebs_sock *sock;
	for (i = 0; i < countof(cxt->socks); i++) {
		sock = &cxt->socks[i];
		if (sock->sockfd >= 0) {
			close(sock->sockfd);
			sock->sockfd = -1;
		}
	}
	free(cxt->buf);
	cxt->buf = NULL;
}

static int recv_mp3_data(struct ebs_sock *sock, unsigned short len)
{
	int left = len;
	int ret;
	unsigned char *mp3buf = sock->cxt->buf;
	while (left) {
		ret = read(sock->sockfd, mp3buf, left);
		if (ret < 0) {
			perror("data:cont:2:read()");
			return ret;	
		}
		left -= ret;

		/* dump to stdout */
		ret = fwrite(mp3buf, 1, ret, stdout);
		if (ret == 0) {
			perror("data:cont:write()");
			return -1;
		}
//		fflush(stdout);
	}
	return 0;
}

/* FIXME: validate properly */
/* MPEG ADTS, layer III, v2,  64 kBits, 24 kHz, JointStereo */
static const unsigned char mp3_magic[4] = { 0xff, 0xf3, 0x84, 0x64};
int scan_and_recv_mp3_data(struct ebs_sock *sock, unsigned short len)
{
	int left = len;
	int pt = 0, i;
	int ret, found;
	unsigned char *mp3buf = sock->cxt->buf;

	while (left) {
		ret = read(sock->sockfd, mp3buf + pt, left);
		if (ret < 0) {
			perror("data:cont:2:read()");
			return ret;	
		}
		left -= ret;
		pt += ret;
	}

	found = -1;
	for (i = 0; i < len - sizeof(mp3_magic); i++) {
		if (!memcmp(mp3buf + i, mp3_magic, sizeof(mp3_magic))) {
			found = i;
			break;
		}
	}
	if (found < 0) {
		fprintf(stderr, "not found\n");
		return -1;
	}
	fprintf(stderr, "@%d\n", found);

	/* swich */
	sock->cxt->recv_data = recv_mp3_data;

	ret = fwrite(mp3buf + found, 1, len - found, stdout);
	if (ret == 0) {
		perror("data:cont:write()");
		return -1;
	}
//	fflush(stdout);
	return 0;
}

int data_rx_handler(struct ebs_sock *sock)
{
	unsigned char packet_r[288] = { PACKET_R };
	unsigned char dummy_buf[288];
	unsigned short this_len;
	int ret;

	switch (sock->state) {
	case ST_IDLE:
		fprintf(stderr, "data:cur:ST_IDLE\n");
		sock->rx_handler = data_rx_handler;

		packet_r[20] = req_tok1[0];
		packet_r[21] = req_tok1[1];
		packet_r[22] = req_tok1[2];
		packet_r[23] = req_tok1[3];
		
		sock->state = ST_DATA_START;
		ret = write(sock->sockfd, packet_r, sizeof(packet_r));
		if (ret < 0) {
			sock->state = ST_ERROR;
			perror("data:idle:write()");
			break;
		}
		fprintf(stderr, "data:to:ST_DATA_START\n");
		break;
	case ST_DATA_START:
		fprintf(stderr, "data:cur:ST_DATA_START\n");
		ret = read(sock->sockfd, dummy_buf, sizeof(dummy_buf));
		if (ret < 0) {
			perror("data:start:read()");
			sock->state = ST_ERROR;
			return ret;
		}
		
		sock->state = ST_DATA_LOOP;
		fprintf(stderr, "data:to:ST_DATA_LOOP\n");
		break;
	case ST_DATA_LOOP:
		ret = read(sock->sockfd, dummy_buf, 32); /* EBS header */
		if (ret < 0) {
			perror("data:start:read()");
			sock->state = ST_ERROR;
			return ret;
		}
		this_len = (dummy_buf[19] << 8) | dummy_buf[18];
		fprintf(stderr, "%u/%d\n",  this_len, ret);

#if 0
		ret = recv_mp3_data(sock, this_len);
#else
		ret = sock->cxt->recv_data(sock, this_len);
#endif
		if (ret < 0) {
			sock->state = ST_ERROR;
			return ret;
		}
		break;
	default:
		fprintf(stderr, "data: unknown state\n");
		return -1;
	}
	return 0;
}

int make_data_connection(context_t *cxt)
{
	int ret;
	ret = make_sock(&cxt->socks[DATA_SOCK], SERVER_IP, DATA_PORT);
	if (ret < 0) {
		return ret;
	}
	return data_rx_handler(&cxt->socks[DATA_SOCK]);
}

static int dummy_rx_handler(struct ebs_sock *sock)
{
	/* do nothing */
	return 0;
}

static context_t *ping_cxt;
static void alarm_handler(int sig)
{
	int ret;
	struct ebs_sock *sock = &ping_cxt->socks[CTL_SOCK];

	ret = write(sock->sockfd, packet_0, sizeof(packet_0));
	if (ret < 0) {
		perror("ping:write()");
		sock->state = ST_ERROR;
		return;
	}

	alarm(PING_INTERVAL);
}

static int prepare_ctl_ping_loop(context_t *cxt)
{
	ping_cxt = cxt;
	signal(SIGALRM, alarm_handler);
	alarm(PING_INTERVAL);
	return 0;
}

static int ctl1_rx_handler(struct ebs_sock *sock)
{
	int ret;
	unsigned char dummy_buf[288];

	switch (sock->state) {
	case ST_IDLE:
		fprintf(stderr, "cur: ST_IDLE\n");
		sock->state = ST_CTL_START;
		sock->rx_handler = ctl1_rx_handler;
		ret = write(sock->sockfd, packet_0, sizeof(packet_0));
		if (ret < 0) {
			perror("ctl:idle:write()");
			sock->state = ST_ERROR;
			return ret;
		}
		fprintf(stderr, "to: ST_CTL_START\n");
		break;
	case ST_CTL_START:
		fprintf(stderr, "cur: ST_CTL_START\n");
		ret = read(sock->sockfd, dummy_buf, sizeof(dummy_buf));
		if (ret < 0) {
			perror("ctl:start:read()");
			sock->state = ST_ERROR;
			return ret;
		}
		fprintf(stderr, "[%s]\n", &dummy_buf[36]);

		sock->state = ST_CTL_PREPARE_REQ;
		ret = write(sock->sockfd, packet_1, sizeof(packet_1));
		if (ret < 0) {
			perror("ctl:start:write()");
			sock->state = ST_ERROR;
			return ret;
		}
		fprintf(stderr, "to: ST_CTL_PREPARE_REQ\n");
		break;
	case ST_CTL_PREPARE_REQ:
		fprintf(stderr, "cur: ST_CTL_PREPARE_REQ\n");
		ret = read(sock->sockfd, dummy_buf, sizeof(dummy_buf));
		if (ret < 0) {
			perror("ctl:prepare_req:read()");
			sock->state = ST_ERROR;
			return ret;
		}
		req_tok1[0] = dummy_buf[20];
		req_tok1[1] = dummy_buf[21];
		req_tok1[2] = dummy_buf[22];
		req_tok1[3] = dummy_buf[23];
		fprintf(stderr, "[0x%02x 0x%02x 0x%02x 0x%02x]\n",
				req_tok1[0], req_tok1[1],
				req_tok1[2], req_tok1[3]
		);

		sock->state = ST_CTL_MAKE_REQ_1;
		ret = write(sock->sockfd, packet_2, sizeof(packet_2));
		if (ret < 0) {
			perror("ctl:prepare_req:write()");
			sock->state = ST_ERROR;
			return ret;
		}
		fprintf(stderr, "to: ST_CTL_MAKE_REQ_1\n");
		break;
	case ST_CTL_MAKE_REQ_1:
		fprintf(stderr, "cur: ST_CTL_MAKE_REQ_1\n");
		ret = read(sock->sockfd, dummy_buf, sizeof(dummy_buf));
		if (ret < 0) {
			perror("ctl:make_req_1:read()");
			sock->state = ST_ERROR;
			return ret;
		}

		sock->state = ST_CTL_MAKE_REQ_2;
		ret = write(sock->sockfd, packet_0, sizeof(packet_0));
		if (ret < 0) {
			perror("ctl:make_req_1:write()");
			sock->state = ST_ERROR;
			return ret;
		}
		fprintf(stderr, "to: ST_CTL_MAKE_REQ_2\n");
		break;
	case ST_CTL_MAKE_REQ_2:
		fprintf(stderr, "cur: ST_CTL_MAKE_REQ_2\n");
		ret = read(sock->sockfd, dummy_buf, sizeof(dummy_buf));
		if (ret < 0) {
			perror("ctl:make_req_2:read()");
			sock->state = ST_ERROR;
			return ret;
		}

		sock->state = ST_CTL_MAKE_REQ_3;
		ret = write(sock->sockfd, packet_3, sizeof(packet_3));
		if (ret < 0) {
			perror("ctl:make_req_2:write()");
			sock->state = ST_ERROR;
			return ret;
		}
		fprintf(stderr, "to: ST_CTL_MAKE_REQ_3\n");
		break;

	case ST_CTL_MAKE_REQ_3:
		fprintf(stderr, "cur: ST_CTL_MAKE_REQ_3\n");
		ret = read(sock->sockfd, dummy_buf, sizeof(dummy_buf));
		if (ret < 0) {
			perror("ctl:make_req_3:1:read()");
			sock->state = ST_ERROR;
			return ret;
		}
		ret = read(sock->sockfd, dummy_buf, sizeof(dummy_buf));
		if (ret < 0) {
			perror("ctl:make_req_3:2:read()");
			sock->state = ST_ERROR;
			return ret;
		}

		ret = prepare_ctl_ping_loop(sock->cxt);
		if (ret < 0) {
			sock->state = ST_ERROR;
			return ret;
		}

		ret = make_data_connection(sock->cxt);
		if (ret < 0) {
			sock->state = ST_ERROR;
			return ret;
		}

		sock->state = ST_CTL_LOOP;
		fprintf(stderr, "to: ST_CTL_LOOP\n");
		break;

	case ST_CTL_LOOP:
		ret = read(sock->sockfd, dummy_buf, sizeof(dummy_buf));
		if (ret < 0) {
			perror("ctl:loop:read()");
			sock->state = ST_ERROR;
			return ret;
		}
		fprintf(stderr, "[%s]\n", &dummy_buf[36]);

		ret = write(sock->sockfd, packet_3, sizeof(packet_3));
		if (ret < 0) {
			perror("ctl:loop:write()");
			sock->state = ST_ERROR;
			return ret;
		}

		ret = read(sock->sockfd, dummy_buf, sizeof(dummy_buf));
		if (ret < 0) {
			perror("ctl:loop:1:read()");
			sock->state = ST_ERROR;
			return ret;
		}
		ret = read(sock->sockfd, dummy_buf, sizeof(dummy_buf));
		if (ret < 0) {
			perror("ctl:loop:2:read()");
			sock->state = ST_ERROR;
			return ret;
		}
		break;

	default:
		fprintf(stderr, "ctl: unknown state\n");
		return -1;
	}
	return 0;
}

inline int make_recv_fds(context_t *cxt, fd_set *fds)
{
	int i;
	int max_fd = -1;
	struct ebs_sock *sock;

	FD_ZERO(fds);

	for (i = 0; i < countof(cxt->socks); i++) {
		sock = &cxt->socks[i];
		if (sock->sockfd > max_fd)
			max_fd = sock->sockfd;
		if (sock->sockfd >= 0)
			FD_SET(sock->sockfd, fds);
	}
	return max_fd;
}

static int check_rx_and_handle_fds(context_t *cxt, fd_set *fds)
{
	int i, ret;
	struct ebs_sock *sock;
	
	for (i = 0; i < countof(cxt->socks); i++) {
		sock = &cxt->socks[i];
		if ((sock->sockfd >= 0) && FD_ISSET(sock->sockfd, fds)) {
			ret = sock->rx_handler(sock->priv);
			if (ret < 0)
				return ret;
		}
	}
	return 0;
}

static void proc_ebs(context_t *cxt)
{
	int max_fd, ret;
	fd_set rfds;

	ctl1_rx_handler(&cxt->socks[CTL_SOCK]);

	do {
		max_fd = make_recv_fds(cxt, &rfds);
		if (max_fd < 0)
			break;
		ret = select(max_fd + 1, &rfds, NULL, NULL, NULL);
		if ((ret < 0) && (errno != EINTR)) {
			perror("select()");
			break;
		}
		if (ret == 0) {
			/* timed-out */
			continue;
		}

		ret = check_rx_and_handle_fds(cxt, &rfds);
		if (ret < 0)
			break;
	} while (1);
}

inline int zero_context(context_t *cxt)
{
	int i;
	struct ebs_sock *sock;

	cxt->buf = malloc(65536);
	if (!cxt->buf) {
		perror("malloc()");
		return -1;
	}

	for (i = 0; i < countof(cxt->socks); i++) {
		sock = &cxt->socks[i];
		sock->sockfd = -1;
		sock->state = ST_IDLE;
		sock->rx_handler = dummy_rx_handler;
		sock->priv = sock;
		sock->cxt = cxt;
	}
	cxt->recv_data = scan_and_recv_mp3_data;

	return 0;
}

int main(int argc, char **argv)
{
	int ret;
	context_t context;

	if (zero_context(&context) < 0) {
		return EXIT_FAILURE;
	}

	ret = make_sock(&context.socks[CTL_SOCK], SERVER_IP, CTL_PORT);
	if (ret < 0) {
		destroy_context(&context);
		return EXIT_FAILURE;
	}

	proc_ebs(&context);

	destroy_context(&context);

	return EXIT_SUCCESS;
}
