import queue
import json
import socket
import select
from threading import Thread
from datetime import datetime
import os
import sys, errno
from signal import signal, SIGPIPE, SIG_DFL

class EventManager:
    def __init__(self):
        self.listeners = []
        self.publisher_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listener_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def handle_publishers(self, publisher_socket, listeners):
        while True:
            client, addr = publisher_socket.accept()
            print(f"Publisher connected: {addr}")
            try:
                with client:
                    data = client.recv(4096)
                    json_data = json.loads(data.decode())
                    print(f"Received data from {addr}: {json_data}")
                    remove_list = []
                    for listener in listeners:
                        try:
                            listener.settimeout(5.0)  # Setting a write timeout
                            listener.sendall(data)
                        except IOError as e:
                            print(f"Error writing to listener {listener.getpeername()}, removing from list")
                            listener.close()
                            remove_list.append(listener)
                        except (socket.timeout, socket.error):
                            print(f"Error writing to listener {listener.getpeername()}, removing from list")
                            listener.close()
                            remove_list.append(listener)
                    for l in remove_list:
                        listeners.remove(l)
            except json.JSONDecodeError:
                print("Failed to decode JSON.")
            except socket.error as e:
                print(f"Error with publisher {addr}: {e}")

    def handle_listeners(self, listener_socket, listeners):
        while True:
            client, addr = listener_socket.accept()
            print(f"Listener connected: {addr}")
            listeners.append(client)

    def start_listeners(self):
        try:
            self.publisher_socket.bind(('', 5000))
            self.listener_socket.bind(('', 5001))
            self.publisher_socket.listen()
            self.listener_socket.listen()

            signal(SIGPIPE, SIG_DFL)

            # Threads to handle each port independently
            publisher_thread = Thread(target=self.handle_publishers,
                                      args=(self.publisher_socket, self.listeners))
            listener_thread = Thread(target=self.handle_listeners,
                                     args=(self.listener_socket, self.listeners))
            publisher_thread.start()
            listener_thread.start()
            print("Event server started. Listening for publishers on port 5000 and listeners on port 5001.")
        except Exception as e:
            pass


