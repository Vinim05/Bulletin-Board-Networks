import socket
import threading

HOST = "0.0.0.0"
PORT = 5000

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