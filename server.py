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
                "sender": message["sender"]
                "date": message["date"]
                "subject": message["subject"]
            }
        }, exclude=username)
        return message

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
                break

            if not isinstance(request, dict):
                send_json(client_socket, {
                    "type": "error",
                    "message": "Invalid Request."
                })
                continue

            if request.get("type") == "post":
                subject = request.get("subject")
                content = request.get("content")

                if not isinstance(subject, str) or not subject.strip():
                    send_json(client_socket, {
                        "type": "error",
                        "message": "Message content cannot be empty."
                    })
                    continue

                message = post_message(
                    username, subject.strip(),
                    content.strip()
                )

                send_json(client_socket, {
                    "type": "message_posted",
                    "message_id": message["id"]
                })

            else:
                send_json(client_socket, {
                    "type": "error",
                    "message": "Unkown request type."
                })

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