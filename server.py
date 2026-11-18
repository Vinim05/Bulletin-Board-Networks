import socket
import threading
import json
from datetime import datetime 

HOST = "0.0.0.0"
PORT = 5000 #

clients = {} #maps usernames
messages = [] #stores messages
next_message_id = 1 #gives messages an ID

lock = threading.Lock() #protects shared data

def broadcast(data, exclude=None): #sends data to all clients except the excluded one
    with lock:
        recipients = [
            client_socket
            for username, client_socket in clients.items()
            if username != exclude
        ]
    for client_socket in recipients:
        try:
            send_json(client_socket, data)
        except OSError:
            pass #ignores errors if client has disconnected


def post_message(username, subject, content):
    global next_message_id #lets function update counter defined outside it

    with lock: #prevents concurrent threads from assigning same message ID
        message = {
            "id": next_message_id,
            "sender": username,
            "date": datetime.now().isoformat( #records when message was posted
                timespec="seconds"
            ),
            "subject": subject,
            "content": content
        }

        messages.append(message) #stores the entire message
        next_message_id += 1

    broadcast({ #sends a summary to all connected users except sender
        "type": "new_message",
        "message": {
            "id": message["id"],
            "sender": message["sender"],
            "date": message["date"],
            "subject": message["subject"]
        }
    }, exclude=username)
    return message

def get_message(message_id): #gets a message by its ID
    with lock:
        for message in messages:
            if message["id"] == message_id:
                return message.copy() #returns a copy of the message to avoid accidental modification
    return None

def get_users():
    with lock:
        return list(clients.keys()) #returns a list of usernames

    
def send_json(client_socket, data): #sends a Python dictionary as JSON to the client
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

        # STEP 1: Register the client
        while username is None:
            request = receive_json(client_file)

            if request is None:
                return

            if not isinstance(request, dict):
                send_json(client_socket, {
                    "type": "error",
                    "message": "Invalid request."
                })
                continue

            if request.get("type") != "join":
                send_json(client_socket, {
                    "type": "error",
                    "message": "Please provide a username."
                })
                continue

            requested_username = request.get("username")

            if not isinstance(requested_username, str):
                send_json(client_socket, {
                    "type": "error",
                    "message": "Invalid username."
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
                    username_available = True

                    previous_users = list(clients.keys())

                    recent_messages = [
                        {
                            "id": msg["id"],
                            "sender": msg["sender"],
                            "date": msg["date"],
                            "subject": msg["subject"]
                        }
                        for msg in messages[-2:]
                    ]

                    clients[requested_username] = client_socket
                    username = requested_username

            if not username_available:
                send_json(client_socket, {
                    "type": "error",
                    "message": "Username is already taken."
                })
                continue

            send_json(client_socket, {
                "type": "joined",
                "username": username,
                "users": previous_users,
                "recent_messages": recent_messages
            })

            broadcast({
                "type": "user_joined",
                "username": username
            }, exclude=username)

            print(f"{username} joined from {client_address}")

        # STEP 2: Handle requests from registered clients
        while True:
            request = receive_json(client_file)

            if request is None:
                break

            if not isinstance(request, dict):
                send_json(client_socket, {
                    "type": "error",
                    "message": "Invalid request."
                })
                continue

            request_type = request.get("type")

            if request_type == "post":
                subject = request.get("subject")
                content = request.get("content")

                if not isinstance(subject, str) or not subject.strip():
                    send_json(client_socket, {
                        "type": "error",
                        "message": "Subject cannot be empty."
                    })
                    continue

                if not isinstance(content, str) or not content.strip():
                    send_json(client_socket, {
                        "type": "error",
                        "message": "Message content cannot be empty."
                    })
                    continue

                message = post_message(
                    username,
                    subject.strip(),
                    content.strip()
                )

                send_json(client_socket, {
                    "type": "message_posted",
                    "message_id": message["id"]
                })

            elif request_type == "users":
                send_json(client_socket, {
                    "type": "user_list",
                    "users": get_users()
                })

            elif request_type == "message":
                message_id = request.get("message_id")

                try:
                    message_id = int(message_id)
                except (ValueError, TypeError):
                    send_json(client_socket, {
                        "type": "error",
                        "message": "Invalid message ID."
                    })
                    continue

                message = get_message(message_id)

                if message is None:
                    send_json(client_socket, {
                        "type": "error",
                        "message": "Message not found."
                    })
                else:
                    send_json(client_socket, {
                        "type": "message_content",
                        "message": message
                    })

            elif request_type == "leave":
                send_json(client_socket, {
                    "type": "left",
                    "message": "Successfully left the board."
                })
                break

            else:
                send_json(client_socket, {
                    "type": "error",
                    "message": "Unknown request type."
                })

    except (ConnectionError, OSError, json.JSONDecodeError) as error:
        print(f"Connection error with {client_address}: {error}")

    finally:
        if username is not None:
            with lock:
                clients.pop(username, None)

            broadcast({
                "type": "user_left",
                "username": username
            })

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