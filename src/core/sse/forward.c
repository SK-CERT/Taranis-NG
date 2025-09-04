#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <sys/poll.h>
#include <getopt.h>

#define PEER_POOL_INCREMENT 1024
#define DEFAULT_MESSAGE_SIZE 512

// this must be much higher than the expected message size, because clients may not be
// scheduled before multiple messages are received and buffered for transmission.
#define CLIENT_BUFFER_SIZE 16384
#define PEER_TYPE_SENDER 0
#define PEER_TYPE_CLIENT 1

#define PORT_SENDER 50000
#define PORT_CLIENT 50001

struct client_s {
    char circular_buffer[CLIENT_BUFFER_SIZE];
    int head; // append end
    int tail; // read end
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
static int verbose_level; // 1-nothing 2-malloc 3-input 4-parser 5-all

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

void hangup_peers() {
    for (int i = n_peers - 1; i >= 2; i--) {
        if (will_hangup(i)) {
            hangup_peer(i);
        }
    }
}

int setup_server_socket(int port) {
    int sockfd = socket(AF_INET, SOCK_STREAM, 0);
    if (sockfd < 0) {
        perror("Socket creation failed");
        exit(EXIT_FAILURE);
    }

    int opt = 1;
    setsockopt(sockfd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

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
        if (!peers_realloc || !fds_realloc)
            return -1;
        max_peers += PEER_POOL_INCREMENT;
    }

    bzero(&peers[n_peers], sizeof(struct peer_s));
    peers[n_peers].fd = accept(listenfd, NULL, NULL);
    if (peers[n_peers].fd == -1) {
        perror("Accept failed");
        return -1;
    }
    peers[n_peers].type = peer_type;
    fds[n_peers].fd = peers[n_peers].fd;

    if (peer_type == PEER_TYPE_SENDER) {
        char *new_buf = malloc(DEFAULT_MESSAGE_SIZE);
        if (verbose_level == 2 || verbose_level == 5)
            printf("Sender peer %d fd %d malloc %d = %p\n", n_peers, peers[n_peers].fd, DEFAULT_MESSAGE_SIZE, new_buf);
        if (new_buf == NULL) {
            perror("Malloc failed");
            shutdown(peers[n_peers].fd, 2);
            close(peers[n_peers].fd);
            return -1;
        }
        peers[n_peers].extra.sender.message = new_buf;
        peers[n_peers].extra.sender.msg_len = 0;
        peers[n_peers].extra.sender.msg_max_len = DEFAULT_MESSAGE_SIZE;
        fds[n_peers].events = POLLIN;
    } else {
        fds[n_peers].events = POLLIN;
    }
    fds[n_peers].revents = 0;
    return n_peers++;
}

int append_to_peer(int index, char *buf, int len) {
    if (peers[index].type != PEER_TYPE_CLIENT)
        return -1;

    struct client_s *client = &peers[index].extra.client;

    int space_remaining = (client->tail - client->head + CLIENT_BUFFER_SIZE - 1) % CLIENT_BUFFER_SIZE;
    int space_until_wrap = CLIENT_BUFFER_SIZE - client->head;

    if (space_remaining < len) {
        // cannot append the message for the client; kick it out
        return -1;
    }
    if (len <= space_until_wrap) {
        memcpy(client->circular_buffer + client->head, buf, len);
    } else {
        memcpy(client->circular_buffer + client->head, buf, space_until_wrap);
        memcpy(client->circular_buffer, buf + space_until_wrap, len - space_until_wrap);
    }
    client->head = (client->head + len) % CLIENT_BUFFER_SIZE;
    return 0;
}

int receive_jsons(int idx) {
    char *new_message_space;
    int jsons_received = 0;

    if (peers[idx].extra.sender.msg_len == peers[idx].extra.sender.msg_max_len) {
        new_message_space = realloc(peers[idx].extra.sender.message,
                                    peers[idx].extra.sender.msg_max_len + DEFAULT_MESSAGE_SIZE);
        if (new_message_space == NULL) {
            perror("Cannot resize sender buffer");
            return -1;
        }
        peers[idx].extra.sender.message = new_message_space;
        peers[idx].extra.sender.msg_max_len += DEFAULT_MESSAGE_SIZE;
    }

    if (verbose_level == 3 || verbose_level == 5)
        printf("From client %d reading %d bytes frk  %p(originally %p)\n", idx,
               peers[idx].extra.sender.msg_max_len - peers[idx].extra.sender.msg_len,
               peers[idx].extra.sender.message + peers[idx].extra.sender.msg_len, peers[idx].extra.sender.message);
    int len = read(peers[idx].fd,
                   peers[idx].extra.sender.message + peers[idx].extra.sender.msg_len,
                   peers[idx].extra.sender.msg_max_len - peers[idx].extra.sender.msg_len);
    if (verbose_level == 3 || verbose_level == 5) printf("Reads %d bytes\n", len);

    if (len <= 0) {
        // remote side closed connection
        if (verbose_level == 3 || verbose_level == 5)
            printf("Preparing to hang client %d fd %d, due to len=0\n", idx, peers[idx].fd);
        prepare_for_hangup(idx);
        return -1;
    }
    peers[idx].extra.sender.msg_len += len;

    while (1) {
        int brackets = 0;
        int in_string = 0; /* 0, 1, 2 */
        int i;
        for (i = 0; i < peers[idx].extra.sender.msg_len; i++) {
            if (verbose_level == 4 || verbose_level == 5)
                printf("Processing character [%c], in_string:%d, i:%d/%d, brackets:%d\n",
                       (peers[idx].extra.sender.message[i] >= 32 && peers[idx].extra.sender.message[i] < 127)
                       ? peers[idx].extra.sender.message[i] : '.', in_string, i, peers[idx].extra.sender.msg_len,
                       brackets);
            if (in_string) {
                if (in_string == 2) {
                    if (verbose_level == 4 || verbose_level == 5) printf("Ignore this character\n");
                    in_string = 1;
                    continue;
                }
                if (peers[idx].extra.sender.message[i] == '"') {
                    if (verbose_level == 4 || verbose_level == 5) printf("Ending  quotation marks\n");
                    in_string = 0;
                    continue;
                }
                if (peers[idx].extra.sender.message[i] == '\\') {
                    if (verbose_level == 4 || verbose_level == 5) printf("Beginning of backslash, ignore rest\n");
                    in_string = 2;
                    continue;
                }
                continue;
            }
            if (verbose_level == 4 || verbose_level == 5) printf("Not in string\n");
            if (peers[idx].extra.sender.message[i] == '{') {
                if (verbose_level == 4 || verbose_level == 5) printf("Start of bracket\n");
                brackets++;
            } else if (peers[idx].extra.sender.message[i] == '}') {
                if (verbose_level == 4 || verbose_level == 5) printf("End of bracket\n");
                brackets--;
                if (brackets <= 0) {
                    if (verbose_level == 4 || verbose_level == 5) printf("Last bracket was send\n");
                    break;
                }
            } else if (peers[idx].extra.sender.message[i] == '"') {
                if (verbose_level == 4 || verbose_level == 5) printf("Start of string\n");
                in_string = 1;
                continue;
            }
        }
        if (verbose_level == 4 || verbose_level == 5) printf("==== END OF PROCESSING ====\n");
        if (i == peers[idx].extra.sender.msg_len) {
            if (verbose_level == 4 || verbose_level == 5) printf("Message not found\n");
            // no new messages
            break;
        }
        // we have a complete JSON to send out; store it in the output buffers
        jsons_received++;

        for (int j = 2; j < n_peers; j++) {
            if (peers[j].type == PEER_TYPE_CLIENT) {
                if (append_to_peer(j, peers[idx].extra.sender.message, i + 1) == -1) {
                    // kick the client, it doesn't empty its ring buffer fast enough
                    prepare_for_hangup(j);
                }
            }
        }

        if (peers[idx].extra.sender.msg_len - i - 1 > 0)
            memmove(peers[idx].extra.sender.message, peers[idx].extra.sender.message + i + 1,
                    peers[idx].extra.sender.msg_len - i - 1);

        peers[idx].extra.sender.msg_len -= i + 1;
    }
    return jsons_received;
}

void do_send_to_client(int index) {
    struct client_s *client;
    int bytes_to_send, bytes_sent;

    if (will_hangup(index) || peers[index].type != PEER_TYPE_CLIENT)
        return;
    client = &peers[index].extra.client;

    if (client->tail == client->head)
        return;

    if (client->head > client->tail) { // no wrap necessary
        bytes_to_send = client->head - client->tail;
    } else { // data wraps; let's send just the first part right now
        bytes_to_send = CLIENT_BUFFER_SIZE - client->tail;
    }
    bytes_sent = write(peers[index].fd,
                       client->circular_buffer + client->tail,
                       bytes_to_send
    );
    if (bytes_sent <= 0) {
        prepare_for_hangup(index);
    } else {
        client->tail = (client->tail + bytes_sent) % CLIENT_BUFFER_SIZE;
    }
}

void print_help(char *self_name, int sender_port, int client_port) {
    printf("Usage: %s [OPTIONS]\n", self_name);
    printf("Options:\n");
    printf("  -h, --help            Display this help message and quit\n");
    printf("  -v, --verbose         Increase verbose level (up to 5)\n");
    printf("  -s <PORT>, --sender-port <PORT>    Set sender port number (current value: %d)\n", sender_port);
    printf("  -c <PORT>, --client-port <PORT>    Set client port number (current value: %d)\n", client_port);
}

void main(int argc, char *argv[]) {
    verbose_level = 0;
    int sender_port = 5000;
    int client_port = 5001;
    int opt;

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

    // parse options
    while (1) {
        static struct option long_options[] = {
                {"help",        no_argument,       0, 'h'},
                {"verbose",     optional_argument, 0, 'v'},
                {"sender-port", required_argument, 0, 's'},
                {"client-port", required_argument, 0, 'c'},
                {0,             0,                 0, 0}
        };
        int option_index = 0;

        opt = getopt_long(argc, argv, "hv:s:c:", long_options, &option_index);

        if (opt == -1) {
            break;
        }

        switch (opt) {
            case 'h':
                print_help(argv[0], sender_port, client_port);
                exit(0);
            case 'v':
                if (optarg) {
                    verbose_level = atoi(optarg);
                } else {
                    verbose_level = 1;
                }
                if (verbose_level > 5) {
                    verbose_level = 5;
                }
                break;
            case 's':
                sender_port = atoi(optarg);
                if (sender_port < 1 || sender_port > 65535) {
                    fprintf(stderr, "Error: Sender port must be between 1 and 65535\n");
                    exit(1);
                }
                break;
            case 'c':
                client_port = atoi(optarg);
                if (client_port < 1 || client_port > 65535) {
                    fprintf(stderr, "Error: Client port must be between 1 and 65535\n");
                    exit(1);
                }
                break;
            default:
                print_help(argv[0], sender_port, client_port);
                exit(1);
        }
    }

    peers[0].type = -1;
    peers[0].fd = setup_server_socket(sender_port);
    fds[0].fd = peers[0].fd;
    fds[0].events = POLLIN;

    peers[1].type = -1;
    peers[1].fd = setup_server_socket(client_port);
    fds[1].fd = peers[1].fd;
    fds[1].events = POLLIN;

    // main loop
    while (1) {
        // modify poll() preferences for consumers
        for (int i = 2; i < n_peers; i++) {
            if (peers[i].type != PEER_TYPE_CLIENT || will_hangup(i))
                continue;
            if (peers[i].extra.client.head == peers[i].extra.client.tail)
                fds[i].events = POLLIN;
            else
                fds[i].events = POLLIN | POLLOUT;
        }
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

        // handle disconnecting clients
        for (int i = 2; i < n_peers; i++) {
            if (will_hangup(i) || !(fds[i].revents & (POLLERR | POLLHUP | POLLNVAL)))
                continue;

            prepare_for_hangup(i);
        }

        // handle output first
        for (int i = 2; i < n_peers; i++) {
            if (will_hangup(i) || !(fds[i].revents & POLLOUT))
                continue;
            do_send_to_client(i);
        }

        // last, handle new inputs
        for (int i = 2; i < n_peers; i++) {
            if (will_hangup(i) || !(fds[i].revents & POLLIN))
                continue;

            if (peers[i].type == PEER_TYPE_CLIENT) {
                char toilet[512];
                if (read(peers[i].fd, toilet, sizeof(toilet)) <= 0)
                    prepare_for_hangup(i);
            } else {
                receive_jsons(i);
            }
        }

        // hangup some peers
        hangup_peers();
    }
}
