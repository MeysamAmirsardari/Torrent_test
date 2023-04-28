# Meysam Amirsardari - 98106218
import asyncio
import socket
import sys
import threading
import time

BUFFER_SIZE = 1024
HEARTBEAT_INTERVAL = 10
HEARTBEAT_TIMEOUT = 30


class Tracker:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.peers = {}
        self.files = {}
        self.lock = threading.Lock()
        self.files_log = []
        self.requests_log = []
        self.sock = None

    def start(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((self.ip, self.port))

        # print(f"Tracker started on {self.ip}:{self.port}")

        self.sock = sock
        thr = threading.Thread(target=self.handle_requests)
        thr.start()
        # self.handle_requests(sock)
        threading.Thread(target=self.heartbeat_thread).start()

    def heartbeat_thread(self):
        while True:
            with self.lock:
                for peer in self.peers:
                    for addr, last_heartbeat in self.peers[peer].items():
                        if time.time() - last_heartbeat > HEARTBEAT_TIMEOUT:
                            del self.peers[peer][addr]
                            print(f"{addr} removed from {peer}")
                            self.requests_log.append(f"Heartbeat timeout from {peer} at {addr}")
            time.sleep(HEARTBEAT_TIMEOUT)

    def handle_requests(self):
        sock = self.sock
        while True:
            data, addr = sock.recvfrom(1024)
            request = data.decode().split()

            if request[0] == "share":
                with self.lock:
                    if request[2] not in self.peers:
                        # print(request[2])
                        self.peers[request[2]] = {}

                    # self.peers[request[2]][addr] = request[1]

                with self.lock:
                    if request[1] not in self.files:
                        self.files[request[1]] = set()

                    self.files[request[1]].add(addr)
                    sock.sendto("OK".encode(), addr)

                with self.lock:
                    self.requests_log.append(f"share {request[1]} from {addr}: successful")

                print(f"Added {request[1]} from {addr}")
                # print(self.files)
                # print(self.peers)

            elif request[0] == "get":
                # print(request)
                with self.lock:
                    if request[3] in self.files:
                        # print(self.files[request[3]])
                        peer_list = ",".join([f"{peer[0]}:{peer[1]}" for peer in self.files[request[3]]])
                        sock.sendto(peer_list.encode(), addr)

                        self.requests_log.append(f"get {request[3]} from {addr}: successful")
                        print(f"Sent peer list for {request[3]} to {addr}")
                    else:
                        sock.sendto("None".encode(), addr)
                        self.requests_log.append(f"get {request[2]} from {addr}: unsuccessful: file not found")
                        print(f"File not found: {request[3]}")

            elif request[0] == "heartbeat":
                with self.lock:
                    sock.sendto("OK".encode(), addr)
                    if request[2] in self.peers:
                        if addr in self.peers[request[2]]:
                            self.peers[request[2]][addr] = time.time()
                        else:
                            self.peers[request[2]][addr] = time.time()
                    else:
                        self.peers[request[2]] = {addr: time.time()}

                    print(f"Heartbeat from {request[2]} at {addr}")
                    self.requests_log.append(f"Heartbeat from {request[2]} at {addr}")

            # elif request[0] == "heartbeat":
            #     with self.lock:
            #         if request[2] in self.peers and addr in self.peers[request[2]]:
            #             self.peers[request[2]][addr] = time.time()
            #             sock.sendto("OK".encode(), addr)
            #             print(f"Heartbeat from {request[2]} at {addr}")
            #             self.requests_log.append(f"Heartbeat from {request[2]} at {addr}")
            #
            #             to_remove = []
            #             for file, peers in self.files.items():
            #                 for peer, timestamp in peers.items():
            #                     if peer[0] == addr[0] and peer[1] == addr[1]:
            #                         if time.time() - timestamp > HEARTBEAT_TIMEOUT:
            #                             to_remove.append((file, peer))
            #
            #             for file, peer in to_remove:
            #                 self.files[file].remove(peer)
            #                 print(f"Removed {peer} from {file}")
            #
            #             to_remove = []
            #             for peer, timestamps in self.peers.items():
            #                 for peer_addr, timestamp in timestamps.items():
            #                     if peer_addr[0] == addr[0] and peer_addr[1] == addr[1]:
            #                         if time.time() - timestamp > HEARTBEAT_TIMEOUT:
            #                             to_remove.append(peer)
            #
            #             for peer in to_remove:
            #                 del self.peers[peer]
            #                 print(f"Removed {peer} from peers list")
            else:
                print(f"Unknown request: {data}")

    def get_file_logs_all(self):
        with self.lock:
            if len(self.files_log) == 0:
                print("No file log found")
            else:
                print("File logs:")
                for log in self.files_log:
                    print(log)

    def get_request_logs(self):
        with self.lock:
            if len(self.requests_log) == 0:
                print("No request log found")
            else:
                print("Request logs:")
                for log in self.requests_log:
                    print(log)


async def handle_user_input(tracker):
    while True:
        user_input = await asyncio.get_event_loop().run_in_executor(None, input, "Ready to show the log :)")
        if user_input == "logs_file all":
            if len(tracker.files) == 0:
                print("No file log found")
            else:
                print("File logs:")
                for file in tracker.files:
                    print(file)
                    print(tracker.files[file])
        elif user_input == "logs request":
            if len(tracker.requests_log) == 0:
                print("No request log found")
            else:
                print("Request logs:")
                for log in tracker.requests_log:
                    print(log)
        elif user_input.startswith(">file_logs>"):
            file = user_input.split('>')[2]
            print(f"log for the file {file}")
            print(tracker.files[file])
        else:
            print("Invalid command")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Invalid number of arguments.")
        sys.exit()
    tracker_address = tuple(sys.argv[1].split(":"))

    ip = tracker_address[0]
    port = int(tracker_address[1])
    tracker_address = (ip, port)
    tracker = Tracker(ip, port)
    # asyncio.create_task(tracker.start())
    thread = threading.Thread(target=tracker.start())
    thread.start()
    thread.join()

    print(f"Starting tracker on {ip}:{port}")

    asyncio.run(handle_user_input(tracker))

    # while True:
    #     user_input = input("")
    #     if user_input == "logs request":
    #         t = threading.Thread(target=tracker.get_request_logs())
    #         t.join()
    #     elif user_input == "logs_file all":
    #         t = threading.Thread(target=tracker.get_file_logs_all())
    #         t.join()
    #     else:
    #         print("Invalid command")
