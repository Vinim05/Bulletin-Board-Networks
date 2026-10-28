
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

    except OSError:
        print("Could not connect to server.")
        client_socket.close()
        return None


def send_request(client_socket, request):
    message = json.dumps(request) + "\n"
    client_socket.sendall(message.encode("utf-8"))


def display_response(response):
    status = response.get("status")
    message = response.get("message")
    data = response.get("data") or {}

    if message:
        print(message)

    if status == "error":
        return

    if "users" in data:
        print("Users in public board:")
        for username in data["users"]:
            print("-", username)

    if "messages" in data:
        for msg in data["messages"]:
            display_message(msg)

    if "message_id" in data:
        if "sender" in data:
            display_message(data)
        else:
            print("Message ID:", data["message_id"])


def display_message(msg):
    print("Message ID:", msg.get("message_id"))
    print("Sender:", msg.get("sender"))
    print("Post Date:", msg.get("date"))
    print("Subject:", msg.get("subject"))

    if "body" in msg:
        print("Message:", msg["body"])

    print()


def receive_messages(client_socket, registered, register_result, disconnected):
    try:
        with client_socket.makefile("r", encoding="utf-8") as stream:
            for line in stream:
                response = json.loads(line)

                display_response(response)

                if (response.get("type") == "response"
                        and response.get("action") == "register"):

                    register_result["success"] = (
                        response.get("status") == "success"
                    )
                    registered.set()

    except (OSError, ValueError) as error:
        print("Connection error:", error)

    finally:
        disconnected.set()
        registered.set()
        client_socket.close()
        print("Disconnected from server.")


def handle_command(client_socket, command):

    if command == "%join":
        send_request(client_socket, {
            "action": "join",
            "group": "public"
        })

    elif command == "%post":
        subject = input("Subject: ")
        body = input("Message: ")

        send_request(client_socket, {
            "action": "post",
            "group": "public",
            "subject": subject,
            "body": body
        })

    elif command == "%users":
        send_request(client_socket, {
            "action": "users",
            "group": "public"
        })

    elif command == "%message" or command.startswith("%message "):
        parts = command.split()

        if len(parts) == 2:
            message_id = parts[1]
        elif len(parts) == 1:
            message_id = input("Message ID: ")
        else:
            print("Usage: %message <message_id>")
            return

        if message_id.isdigit() and int(message_id) > 0:
            send_request(client_socket, {
                "action": "message",
                "group": "public",
                "message_id": int(message_id)
            })
        else:
            print("Invalid message ID.")

    elif command == "%leave":
        send_request(client_socket, {
            "action": "leave",
            "group": "public"
        })

    else:
        print("Invalid command.")


def main():
    client_socket = None
    disconnected = None

    print("Welcome to the Bulletin Board!")

    while True:
        try:
            command = input("> ").strip()

            if command == "%exit":
                if client_socket is not None:
                    if not disconnected.is_set():
                        try:
                            send_request(client_socket, {"action": "exit"})
                        except OSError:
                            pass
                break

            elif command.startswith("%connect"):
                if client_socket is not None and not disconnected.is_set():
                    print("Already connected.")
                    continue

                parts = command.split()

                if len(parts) != 3 or parts[0] != "%connect":
                    print("Usage: %connect <host> <port>")
                    continue

                if client_socket is not None:
                    client_socket.close()

                host = parts[1]

                try:
                    port = int(parts[2])
                    if not 1 <= port <= 65535:
                        raise ValueError
                except ValueError:
                    print("Invalid port number.")
                    continue

                client_socket = connect_to_server(host, port)

                if client_socket is None:
                    continue

                registered = threading.Event()
                disconnected = threading.Event()
                register_result = {"success": False}

                receiver = threading.Thread(
                    target=receive_messages,
                    args=(client_socket, registered, register_result, disconnected),
                    daemon=True
                )
                receiver.start()

                while not disconnected.is_set():
                    username = input("Enter username: ").strip()

                    if not username:
                        print("Username cannot be empty.")
                        continue

                    register_result["success"] = False
                    registered.clear()

                    send_request(client_socket, {
                        "action": "register",
                        "username": username
                    })

                    registered.wait()

                    if disconnected.is_set():
                        break

                    if register_result["success"]:
                        break

            elif client_socket is None or disconnected.is_set():
                print("Connect to the server first.")

            else:
                handle_command(client_socket, command)

        except OSError:
            print("Connection error.")
            if client_socket is not None:
                client_socket.close()
            client_socket = None

        except (EOFError, KeyboardInterrupt):
            print("\nClosing client.")
            break

    if client_socket is not None:
        client_socket.close()


if __name__ == "__main__":
    main()
