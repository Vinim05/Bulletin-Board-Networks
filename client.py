import socket
import threading
import json

HOST = "127.0.0.1"
PORT = 5000


def connect_to_server(host, port):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        client_socket.connect((host, port))
        print("Connected to server!")
        return client_socket
    except OSError as error:
        print("Could not connect to server:", error)
        client_socket.close()
        return None


def send_request(client_socket, request):
    message = json.dumps(request) + "\n"
    client_socket.sendall(message.encode("utf-8"))


def close_connection(client_socket):
    try:
        client_socket.shutdown(socket.SHUT_RDWR)
    except OSError:
        pass
    client_socket.close()


def display_message(message):
    print("Message ID:", message.get("id"))
    print("Sender:", message.get("sender"))
    print("Post Date:", message.get("date"))
    print("Subject:", message.get("subject"))
    if "content" in message:
        print("Content:", message["content"])
    print()


def display_response(response):
    response_type = response.get("type")

    if response_type == "username_required":
        print("Type %join to choose a username and join the public board.")

    elif response_type == "joined":
        print("Joined the public board as", response.get("username"))
        users = response.get("users", [])
        print("Users already on the board:", ", ".join(users) if users else "None")
        recent_messages = response.get("recent_messages", [])
        print("Last two messages:")
        if not recent_messages:
            print("No previous messages.")
        for message in recent_messages:
            display_message(message)

    elif response_type == "user_joined":
        print(response.get("username"), "joined the public board.")

    elif response_type == "user_left":
        print(response.get("username"), "left the public board.")

    elif response_type == "new_message":
        print("New message posted:")
        display_message(response.get("message", {}))

    elif response_type == "message_posted":
        print("Message posted! Message ID:", response.get("message_id"))

    elif response_type == "user_list":
        users = response.get("users", [])
        print("Users in public board:")
        for username in users:
            print("-", username)

    elif response_type == "message_content":
        display_message(response.get("message", {}))

    elif response_type == "left":
        print(response.get("message", "Left the public board."))

    elif response_type == "error":
        print("Error:", response.get("message", "Unknown error"))

    else:
        print("Server response:", response)


def receive_messages(client_socket, joined, join_reply, disconnected):
    try:
        with client_socket.makefile("r", encoding="utf-8") as stream:
            for line in stream:
                response = json.loads(line)
                if not isinstance(response, dict):
                    print("Invalid server response.")
                    continue

                response_type = response.get("type")
                if response_type == "joined":
                    joined.set()
                elif response_type == "left":
                    joined.clear()

                display_response(response)

                if response_type == "joined" or (
                    response_type == "error" and not joined.is_set()
                ):
                    join_reply.set()
    except (OSError, ValueError) as error:
        print("Connection error:", error)
    finally:
        disconnected.set()
        join_reply.set()
        client_socket.close()
        print("Disconnected from server.")


def handle_command(client_socket, command, joined, join_reply, disconnected):
    if command == "%join":
        if joined.is_set():
            print("You already joined the public board.")
            return

        username = input("Enter username: ").strip()
        if not username:
            print("Username cannot be empty.")
            return

        join_reply.clear()
        send_request(client_socket, {
            "type": "join",
            "username": username
        })
        if not join_reply.wait(timeout=10):
            print("No response from server. Closing connection.")
            close_connection(client_socket)
        return

    if not joined.is_set():
        print("Join the public board first using %join.")
        return

    if command == "%post":
        subject = input("Subject: ").strip()
        content = input("Message: ").strip()
        send_request(client_socket, {
            "type": "post",
            "subject": subject,
            "content": content
        })

    elif command == "%users":
        send_request(client_socket, {"type": "users"})

    elif command == "%message" or command.startswith("%message "):
        parts = command.split()
        if len(parts) == 2:
            message_id = parts[1]
        elif len(parts) == 1:
            message_id = input("Message ID: ").strip()
        else:
            print("Usage: %message <message_id>")
            return

        if not message_id.isdigit() or int(message_id) <= 0:
            print("Invalid message ID.")
            return

        send_request(client_socket, {
            "type": "message",
            "message_id": int(message_id)
        })

    elif command == "%leave":
        send_request(client_socket, {"type": "leave"})
        # The current server closes the TCP connection after leaving.
        disconnected.wait(timeout=3)

    else:
        print("Invalid command.")


def main():
    client_socket = None
    disconnected = threading.Event()
    disconnected.set()
    joined = threading.Event()
    join_reply = threading.Event()

    print("Welcome to the Bulletin Board!")
    print("Use %connect or %connect <host> <port> to connect.")

    while True:
        try:
            command = input("> ").strip()

            if command == "%exit":
                break

            elif command == "%connect" or command.startswith("%connect "):
                if client_socket is not None and not disconnected.is_set():
                    print("Already connected.")
                    continue

                parts = command.split()
                if len(parts) == 1:
                    host, port = HOST, PORT
                elif len(parts) == 3:
                    host = parts[1]
                    try:
                        port = int(parts[2])
                        if not 1 <= port <= 65535:
                            raise ValueError
                    except ValueError:
                        print("Invalid port number.")
                        continue
                else:
                    print("Usage: %connect <host> <port>")
                    continue

                if client_socket is not None:
                    close_connection(client_socket)

                client_socket = connect_to_server(host, port)
                if client_socket is None:
                    continue

                disconnected = threading.Event()
                joined = threading.Event()
                join_reply = threading.Event()

                receiver = threading.Thread(
                    target=receive_messages,
                    args=(client_socket, joined, join_reply, disconnected),
                    daemon=True
                )
                receiver.start()

            elif client_socket is None or disconnected.is_set():
                print("Not connected. Use %connect to reconnect.")

            else:
                handle_command(client_socket, command, joined, join_reply, disconnected)

        except OSError as error:
            print("Connection error:", error)
            if client_socket is not None:
                close_connection(client_socket)
            client_socket = None

        except (EOFError, KeyboardInterrupt):
            print("\nClosing client.")
            break

    if client_socket is not None:
        close_connection(client_socket)


if __name__ == "__main__":
    main()
