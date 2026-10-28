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

'''This function expects a file-like object created with client_socket.makefile("r", encoding="utf-8").
   It reads one line at a time and converts it into a Python dictionary.'''
def recieve_json(client_file):
    line = client_file.readline()

    if not line:
        return None
    return json.loads(line) 


def handle_client(client_socket, client_address):
    client_file = client_socket.makefile("r", encoding="utf-8")
    username = None

    try: 
        send_json(client_socket, {
            "type": "username_required"
        })

        while True:
            request = recieve_json(client_file)

            if request is None:
                return

            if request.get("type") != "join":
                send_json(client_socket, {
                    "type": "error",
                    "message": "Please provide a username to join."
                })
                continue

            requested_username = request.get("username")

            if not isinstance(requested_username, str):
                send_json(client_socket, {
                    "type": "error",
                    "message": "Username must be text,"
                })
                continue
            requested_username = requested_username.strip()

            if not requested_username:
                send_json(client_socket, {
                    "type": "error",
                    "message": "Username cannot be empty."
                })
                continue

            with lock:
                if requested_username in clients:
                    username_available = False
                else:
                    clients[requested_username] = client_socket
                    username = requested_username
                    username_available = True 

            if not username_available:
                send_json(client_socket, {
                    "type": "error", 
                    "message": "Username is already taken."
                })
                continue
            send_json(client_socket, {
                "type": "joined", 
                "username": username
            })

            print(f"{username} joined from {client_address}")
            break 
    except (ConnectionError, OSError, json.JSONDecodeError) as error:
        print(f"Connection error with {client_address}: {error}")

    finally:
        if username is not None:
            with lock:
                clients.pop(username, None)

            print(f"{username} disconnected")

        client_file.close()
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