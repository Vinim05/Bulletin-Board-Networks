import socket
import threading
import json 

HOST = "0.0.0.0"
PORT = 5000

clients = {} #maps usernames
messages = [] #stores messages
next_message_id = 1 #gives messages an ID

lock = threading.Lock() #protects shared data

def send_json(client_socket, data):
    message = json.dumps(data) + "\n" #converts dict to JSON
    client_socket.sendall(message.encode("utf-8")) #converts to bytes and sends 

def handle_client(client_socket, client_address):
    print(f"Connection from {client_address}")

    client_socket.close()

def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # creates a TCP socket, AF_INET = IPv4, 

    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT)) #attaches to port 5000
    server_socket.listen() 

    print(f"Server is listening on port {PORT}")

    while True:
        client_socket, client_address = server_socket.accept()

        client_thread = threading.Thread(
            target=handle_client, 
            args= (client_socket, client_address)
        )
        client_thread.start()



if __name__ == "__main__":
    start_server()