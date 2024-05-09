#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <sys/poll.h>

#define PEER_POOL_INCREMENT 1024
#define DEFAULT_MESSAGE_SIZE 512
#define PEER_TYPE_SENDER 0
#define PEER_TYPE_CLIENT 1

#define PORT_SENDER 5000
#define PORT_CLIENT 5001

#define DEBUG_PARSER 0
#define DEBUG_INPUT 0
#define DEBUG_MALLOC 0

struct message_queue_s {
    char *message;
    struct message_queue_s *next;
};

struct client_s {
};

struct sender_s {
    char *message;
    int msg_len;
    int msg_max_len;
};

struct peer_s {
    int fd;
    int type;
    union {
        struct client_s client;
        struct sender_s sender;
    } extra;
};

static int n_peers;
static int max_peers;
static struct peer_s *peers;
static struct pollfd *fds;

int setup_server_socket(int port) {
    int sockfd = socket(AF_INET, SOCK_STREAM, 0);
    if (sockfd < 0) {
        perror("Socket creation failed");
        exit(EXIT_FAILURE);
    }

    int opt = 1;
    setsockopt(sockfd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));
    setsockopt(sockfd, SOL_SOCKET, SO_REUSEPORT, &opt, sizeof(opt));

    struct sockaddr_in addr;
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = INADDR_ANY;
    addr.sin_port = htons(port);

    if (bind(sockfd, (struct sockaddr *) &addr, sizeof(addr)) < 0) {
        perror("Socket bind failed");
        exit(EXIT_FAILURE);
    }

    if (listen(sockfd, 10) < 0) {
        perror("Socket listen failed");
        exit(EXIT_FAILURE);
    }

    return sockfd;
}

int accept_peer(int listenfd, int peer_type) {
    if (max_peers == n_peers) {
        struct peer_s *peers_realloc;
        struct pollfd *fds_realloc;

        peers_realloc = realloc(peers, sizeof(struct peer_s) * (max_peers + PEER_POOL_INCREMENT));
        fds_realloc = realloc(fds, sizeof(struct pollfd) * (max_peers + PEER_POOL_INCREMENT));
        if (peers_realloc)
            peers = peers_realloc;
        if (fds_realloc)
            fds = fds_realloc;
        if (!peers_realloc || !peers_realloc)
            return -1;
        max_peers += PEER_POOL_INCREMENT;
    }
    peers[n_peers].fd = accept(listenfd, NULL, NULL);
    if (peers[n_peers].fd == -1) {
        perror("accept failed");
        return -1;
    }
    peers[n_peers].type = peer_type;
    fds[n_peers].fd = peers[n_peers].fd;

    if (peer_type == PEER_TYPE_SENDER) {
        char *new_buf = malloc(DEFAULT_MESSAGE_SIZE);
        if (DEBUG_MALLOC)
            printf("sender peer %d fd %d malloc %d = %p\n", n_peers, peers[n_peers].fd, DEFAULT_MESSAGE_SIZE, new_buf);
        if (new_buf == NULL) {
            perror("malloc failed");
            shutdown(peers[n_peers].fd, 2);
            close(peers[n_peers].fd);
            return -1;
        }
        peers[n_peers].extra.sender.message = new_buf;
        peers[n_peers].extra.sender.msg_len = 0;
        peers[n_peers].extra.sender.msg_max_len = DEFAULT_MESSAGE_SIZE;
        fds[n_peers].events = POLLIN;
    } else {
        fds[n_peers].events = 0;
    }
    fds[n_peers].revents = 0;
    return n_peers++;
}

int will_hangup(int idx) {
    return (peers[idx].fd == -1);
}

void prepare_for_hangup(int idx) {
    shutdown(peers[idx].fd, 2);
    close(peers[idx].fd);
    peers[idx].fd = -1;
}

void hangup_peer(int index) {
    if (peers[index].type == PEER_TYPE_SENDER) {
        if (peers[index].extra.sender.message) {
            free(peers[index].extra.sender.message);
        }
    }
    peers[index] = peers[n_peers - 1];
    fds[index] = fds[n_peers - 1];
    n_peers--;
}

int receive_jsons(int idx) {
    char *new_message_space;
    if (peers[idx].extra.sender.msg_len == peers[idx].extra.sender.msg_max_len) {
        new_message_space = realloc(peers[idx].extra.sender.message,
                                    peers[idx].extra.sender.msg_max_len + DEFAULT_MESSAGE_SIZE);
        if (new_message_space == NULL) {
            perror("cannot resize sender buffer");
            return -1;
        }
        peers[idx].extra.sender.message = new_message_space;
        peers[idx].extra.sender.msg_max_len += DEFAULT_MESSAGE_SIZE;
    }

    if (DEBUG_INPUT)
        printf("Z klienta %d citam %d bajtov od %p(povodne %p)\n", idx,
               peers[idx].extra.sender.msg_max_len - peers[idx].extra.sender.msg_len,
               peers[idx].extra.sender.message + peers[idx].extra.sender.msg_len, peers[idx].extra.sender.message);
    int len = read(peers[idx].fd,
                   peers[idx].extra.sender.message + peers[idx].extra.sender.msg_len,
                   peers[idx].extra.sender.msg_max_len - peers[idx].extra.sender.msg_len);
    if (DEBUG_INPUT) printf("Nacitanych %d bajtov\n", len);

    if (len == 0) {
        // remote side closed connection
        if (DEBUG_INPUT) printf("Idem zlozit klienta %d fd %d, lebo len=0\n", idx, peers[idx].fd);
        prepare_for_hangup(idx);
        return -1;
    }
    peers[idx].extra.sender.msg_len += len;

    while (1) {
        int brackets = 0;
        int in_string = 0; /* 0, 1, 2 */
        int i;
        for (i = 0; i < peers[idx].extra.sender.msg_len; i++) {
            if (DEBUG_PARSER)
                printf("Spracovavam znak [%c], in_string:%d, i:%d/%d, brackets:%d\n",
                       (peers[idx].extra.sender.message[i] >= 32 && peers[idx].extra.sender.message[i] < 127)
                       ? peers[idx].extra.sender.message[i] : '.', in_string, i, peers[idx].extra.sender.msg_len,
                       brackets);
            if (in_string) {
                if (in_string == 2) {
                    if (DEBUG_PARSER) printf("seriem na ten znak\n");
                    in_string = 1;
                    continue;
                }
                if (peers[idx].extra.sender.message[i] == '"') {
                    if (DEBUG_PARSER) printf("koncim uvodzovky\n");
                    in_string = 0;
                    continue;
                }
                if (peers[idx].extra.sender.message[i] == '\\') {
                    if (DEBUG_PARSER) printf("zacal mi backslash, dalsie budem ignorovat\n");
                    in_string = 2;
                    continue;
                }
                continue;
            }
            if (DEBUG_PARSER) printf("nie som v stringu\n");
            if (peers[idx].extra.sender.message[i] == '{') {
                if (DEBUG_PARSER) printf("zacina mi zatvorka\n");
                brackets++;
            } else if (peers[idx].extra.sender.message[i] == '}') {
                if (DEBUG_PARSER) printf("konci mi zatvorka\n");
                brackets--;
                if (brackets <= 0) {
                    if (DEBUG_PARSER) printf("bola posledna\n");
                    break;
                }
            } else if (peers[idx].extra.sender.message[i] == '"') {
                if (DEBUG_PARSER) printf("zacina mi string\n");
                in_string = 1;
                continue;
            }
        }
        if (DEBUG_PARSER) printf("==== KONIEC SPRACOVANIA ====\n");
        if (i == peers[idx].extra.sender.msg_len) {
            if (DEBUG_PARSER) printf("nenasiel som spravu\n");
            // no new messages
            break;
        }
        // we have a complete JSON to send out

        for (int j = 2; j < n_peers; j++) {
            if (peers[j].type == PEER_TYPE_CLIENT) {
                // FIXME: prerobit na vystupne buffre a poll na write
                // lebo toto moze blokovat.. :(
                // FIXME 2: osetrit dlzku write
                write(peers[j].fd, peers[idx].extra.sender.message, i + 1);
                write(peers[j].fd, "\n", 1);
            }
        }

        if (peers[idx].extra.sender.msg_len - i - 1 > 0)
            memmove(peers[idx].extra.sender.message, peers[idx].extra.sender.message + i + 1,
                    peers[idx].extra.sender.msg_len - i - 1);

        peers[idx].extra.sender.msg_len -= i + 1;
    }
    return 0;
}

int main() {
    n_peers = 2;
    max_peers = PEER_POOL_INCREMENT;
    peers = malloc(sizeof(struct peer_s) * max_peers);
    if (!peers) {
        perror("Cannot allocate memory for clients");
        exit(1);
    }
    fds = malloc(sizeof(struct pollfd) * max_peers);
    if (!fds) {
        perror("Cannot allocate memory for clients (fds)");
        exit(1);
    }

    peers[0].type = -1;
    peers[0].fd = setup_server_socket(PORT_SENDER);
    fds[0].fd = peers[0].fd;
    fds[0].events = POLLIN;

    peers[1].type = -1;
    peers[1].fd = setup_server_socket(PORT_CLIENT);
    fds[1].fd = peers[1].fd;
    fds[1].events = POLLIN;

    while (1) {
        int ret = poll(fds, n_peers, -1);
        if (ret < 0) {
            perror("Poll failed");
            sleep(1);
            continue;
        }

        // accept new sender
        if (fds[0].revents & POLLIN) {
            accept_peer(fds[0].fd, PEER_TYPE_SENDER);
        }
        // accept new client
        if (fds[1].revents & POLLIN) {
            accept_peer(fds[1].fd, PEER_TYPE_CLIENT);
        }

        // handle existing senders
        for (int i = 2; i < n_peers; i++) {
            if (!will_hangup(i) && fds[i].revents & POLLIN) {
                receive_jsons(i);
            }
            if (!will_hangup(i) && (fds[i].revents & (POLLERR | POLLHUP | POLLNVAL))) {
                if (DEBUG_INPUT)
                    printf("klient %d fd %d==%d ma revent 0x%04x, zatvaram\n", i, peers[i].fd, fds[i].fd,
                           fds[i].revents);
                prepare_for_hangup(i);
            }
        }

        // close the clients
        for (int i = n_peers - 1; i >= 2; i--) {
            if (will_hangup(i)) {
                hangup_peer(i);
            }
        }

    }

    return 0;
}

