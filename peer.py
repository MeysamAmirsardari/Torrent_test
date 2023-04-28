import asyncio
import concurrent.futures
import random
import socket
import os
import sys
import threading
import time

BUFFER_SIZE = 1024
TRACKER_TIMEOUT = 10


class Peer:
    def __init__(self, ip, port, tracker_address, mode):
        self.ip = "127.0.0.1"
        self.port = port
        self.files = []
        self.connections = {}
        self.mode = mode
        self.tracker_address = tracker_address
        self.responses_log = []
        self.peer_status_log = []

    def start_heartbeats(self):
        heartbeat_thread = threading.Thread(target=self.send_heartbeat)
        heartbeat_thread.daemon = True
        heartbeat_thread.start()

    def send_heartbeat(self):
        while True:
            # Send a heartbeat message to the tracker every 30 seconds
            message = f"heartbeat from {(self.ip, self.port)}"
            response = self.send_udp_message(message, self.tracker_address)

            if response != "OK":
                print(f"Error: {response}")
                self.responses_log.append(f"Heartbeat error: {response}")
            else:
                self.responses_log.append(f"Heartbeat response: {response}")
            time.sleep(10)

    # def say_hello(self):
    #     message = f"Hello from {self.ip}:{self.port}"
    #     response = send_udp_message(message, self.tracker_address)
    #
    #     if response != "OK":
    #         print(f"Error: {response}")
    #     else:
    #         print("connected to the tracker")

    def handle_get_mode(self, filename):
        message = f"get {(self.ip, self.port)} {filename}"
        response = self.send_udp_message(message, self.tracker_address)
        if not response:
            return False

        peers = response.split()
        if len(peers) == 1 and peers[0] == "None":
            print("File not found.")
            self.responses_log.append(f"File not found: {filename}")
            return False
        else:
            self.responses_log.append(f"File found: {filename} on peers: {peers}")
            print(f"Found file on peers: {peers}")

        if len(peers) > 0:
            idx = random.randint(0, len(peers) - 1)
        else:
            idx = 0

        peer_address = peers[idx].split(":")
        file_data = b""

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            # print(peer_address)
            sock.connect((peer_address[0], int(peer_address[1])))
            sock.sendall(filename.encode())
            while True:
                data = sock.recv(BUFFER_SIZE)
                if not data:
                    break
                file_data += data

        self.files.append(filename)
        with open(filename, "wb") as f:
            f.write(file_data)
        print("File downloaded successfully.")
        self.responses_log.append(f"File downloaded successfully: {filename}")
        return True

    def handle_share_mode(self, filename, listen_address):
        message = f"share {filename} {listen_address[0]}:{listen_address[1]}"
        response = self.send_udp_message(message, self.tracker_address)
        if response:
            print(f"Registered with tracker. Response: {response}")
            self.responses_log.append(f"Share mode registered: {filename}, {listen_address}, response: {response}")
        else:
            self.responses_log.append(f"Failed to register with tracker")
            return

        print(f"Listening for requests on {listen_address}...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind((self.ip, self.port))
        sock.listen()

        while True:
            conn, addr = sock.accept()
            print(f"Received request from {addr}.")
            self.responses_log.append(f"Received request from {addr}.")
            threading.Thread(target=handle_share_request, args=(conn, addr)).start()

    async def get_input(self):
        while True:
            request = await asyncio.get_event_loop().run_in_executor(None, input, '')
            if request.lower() == 'request logs':
                print(self.peer_status_log)
                print(self.responses_log)

    async def run(self):
        self.start_heartbeats()
        # asyncio.create_task(self.get_input())

    def send_udp_message(self, message, address):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(TRACKER_TIMEOUT)
        sock.bind((self.ip, self.port))
        try:
            sock.sendto(message.encode(), address)
            response, _ = sock.recvfrom(BUFFER_SIZE)
            sock.close()
            return response.decode()
        except socket.timeout:
            print("Timeout waiting for response from tracker.")
            return None


def handle_share_request(conn, addr):
    with open(filename, "rb") as f:
        data = f.read(BUFFER_SIZE)
        while data:
            conn.sendall(data)
            data = f.read(BUFFER_SIZE)
    conn.close()
    print(f"Sent file to {addr}.")
    return True





async def handle_mode(peer, mode, filename, listen_address):
    # if mode == "share":
    #     await asyncio.to_thread(peer.handle_share_mode, filename, listen_address)
    # elif mode == "get":
    #     asyncio.create_task(peer.handle_get_mode(filename))
    #     asyncio.create_task(peer.handle_share_mode(filename, listen_address))
    if mode == "share":
        peer.handle_share_mode(filename, listen_address)
    elif mode == "get":
        isDone = peer.handle_get_mode(filename)
        if isDone:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                executor.submit(peer.handle_share_mode, filename, listen_address)


async def handle_user_input(peer):
    while True:
        user_input = await asyncio.get_event_loop().run_in_executor(None, input, "Ready to show the log :)")
        if user_input.lower() == 'request logs':
            print(peer.peer_status_log)
            print(peer.responses_log)
        else:
            print("Invalid command")


if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Invalid number of arguments.")
        sys.exit()
    mode = sys.argv[1]
    filename = sys.argv[2]
    tracker_address = tuple(sys.argv[3].split(":"))
    tracker_address = (tracker_address[0], int(tracker_address[1]))

    listen_address = tuple(sys.argv[4].split(":"))
    port = int(listen_address[1])
    ip = listen_address[0]
    listen_address = (ip, port)
    # print(listen_address)

    print(f"peer started at: {ip}:{port}")

    peer = Peer(ip, port, tracker_address, mode)

    # peer.say_hello()
    peer.start_heartbeats()
    # asyncio.run(peer.run())

    # if mode == "share":
    #     peer.handle_share_mode(filename, listen_address)
    # elif mode == "get":
    #     isDone = peer.handle_get_mode(filename)
    #     if isDone:
    #         peer.handle_share_mode(filename, listen_address)

    asyncio.run(handle_mode(peer, mode, filename, listen_address))
    asyncio.run(handle_user_input(peer))
