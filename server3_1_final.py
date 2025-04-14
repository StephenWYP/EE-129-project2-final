# EE129 Project 2 - Final Version with CLI Control + Multi-Client Support

from socket import *   # Import all socket module functions and constants (for TCP/IP networking)
import sys             # Provides access to system-level functions like sys.exit()
import os              # Used to check file existence and interact with the file system
import threading       # For multi-threaded client handling
import select          # For monitoring both stdin and sockets

# Create a TCP server socket
# (AF_INET is used for IPv4 protocols)
# (SOCK_STREAM is used for TCP)
serverSocket = socket(AF_INET, SOCK_STREAM)

# Set the port number
serverPort = 5500

# Bind the socket to server address and server port
serverSocket.bind(("", serverPort))

# Start listening for connections (only 1 at a time, but we'll support multi-thread)
serverSocket.listen(5)  # Allow up to 5 pending connections

# File path to store login stats
stats_file = "login_stats.txt"

# Initialize stats file if not exists
if not os.path.exists(stats_file):
    with open(stats_file, "w") as f:
        f.write("success=0\nfail=0\n")

# Function to handle each client connection
def handle_client(connectionSocket):
    try:
        message = connectionSocket.recv(1024).decode()
        print("Request received:\n", message)

        # Handle POST login submission (form submitted from login page)
        if message.startswith("POST /login"):
            # Split full HTTP request into individual lines
            headers = message.split("\r\n")
            content_length = 0
            # Extract Content-Length to know how many bytes to expect in the body
            for h in headers:
                if h.lower().startswith("content-length:"):
                    content_length = int(h.split(":")[1].strip())
            # The HTTP body starts after a blank line (\r\n\r\n)
            body = message.split("\r\n\r\n")[1]
            # If body is not fully received (e.g., split into multiple packets), continue reading
            while len(body) < content_length:
                body += connectionSocket.recv(1024).decode()
            
            # Parse the form data: "username=user&password=pass" → {'username': ..., 'password': ...}
            params = dict(param.split("=") for param in body.split("&"))
            # Extract the submitted username and password from the parsed data
            username = params.get("username", "")
            password = params.get("password", "")

            # Read the current login statistics from the file
            with open(stats_file, "r") as f:
                lines = f.readlines()
                # Parse the first line to get current number of successful logins
                success = int(lines[0].split("=")[1])
                # Parse the second line to get current number of failed logins
                fail = int(lines[1].split("=")[1])

            # Check submitted credentials against expected values
            if username == "user" and password == "password":
                # Increment success counter
                success += 1
                # Overwrite the stats file with updated values
                with open(stats_file, "w") as f:
                    f.write(f"success={success}\nfail={fail}\n")
                # Prepare the HTML response for a successful login (to be filled below)
                html_response = f"""
                <html>
                    <head>
                        <style>
                            body {{ font-family: Arial; margin: 40px; }}
                            .success {{ color: green; font-size: 20px; }}
                            .fail {{ color: red; font-size: 20px; }}
                        </style>
                    </head>
                    <body>
                        <p class="success">Login Success</p>
                        <p class="success">Successful logins: {success}</p>
                        <p class="fail">Failed logins: {fail}</p>
                    </body>
                </html>
                """
            else:
                fail += 1
                with open(stats_file, "w") as f:
                    f.write(f"success={success}\nfail={fail}\n")
                html_response = """
                <html>
                    <head>
                        <style>
                            body { font-family: Arial; margin: 40px; }
                            .fail { color: red; font-size: 20px; }
                        </style>
                    </head>
                    <body>
                        <p class="fail">Login Failed</p>
                    </body>
                </html>
                """
            # Send HTTP 200 OK response header to the client
            connectionSocket.send("HTTP/1.1 200 OK\r\n\r\n".encode())
            # Send the HTML content of the response (either login success or failure)
            connectionSocket.send(html_response.encode())
            # Close the client connection after sending the response
            connectionSocket.close()
            # Exit the current request handler (if inside a thread or function)
            return

        # Extract the requested path from the first line of the HTTP request
        # Example: "GET /login HTTP/1.1" → "/login"
        requested_path = message.split()[1]

        # If the request is for the login page (GET /login), return the login form
        if requested_path.startswith("/login"):
            login_form = """
            <html>
                <head>
                    <title>Login Page</title>
                    <style>
                        body {
                            font-family: Arial, sans-serif;
                            margin: 40px;
                        }
                        label, input {
                            font-size: 16px;
                        }
                        .submit-btn {
                            font-size: 16px;
                            margin-top: 10px;
                            background-color: #4CAF50;
                            color: white;
                            border: none;
                            padding: 8px 16px;
                            cursor: pointer;
                        }
                    </style>
                </head>
                <body>
                    <h1>Login Page</h1>
                    <form action="/login" method="post">
                        <label for="username">Please enter your username:</label><br>
                        <input type="text" name="username"><br><br>
                        <label for="password">Please enter your password:</label><br>
                        <input type="password" name="password"><br><br>
                        <input class="submit-btn" type="submit" value="Submit">
                    </form>
                </body>
            </html>
            """
            connectionSocket.send("HTTP/1.1 200 OK\r\n\r\n".encode())
            connectionSocket.send(login_form.encode())
            connectionSocket.close()
            return

        # If the request path starts with "/" and includes a color query parameter
        # Example: GET /?color=red → we need to respond with a color message
        if requested_path.startswith("/") and "color=" in requested_path:
            # Extract the query string part after the "?" in the URL
            # Example: "/?color=red" → "color=red"
            query = requested_path.split("?")[1]
            # Split the query string into individual parameters
            # (in case more than one query parameter is passed)
            params = query.split("&")
            # Initialize a variable to hold the selected color
            color_value = None
            # Look for the "color=" parameter and extract its value
            for param in params:
                if param.startswith("color="):
                    color_value = param.split("=")[1]
                    break
            # If the color is valid ("red" or "green"), prepare an HTML response
            if color_value == "red" or color_value == "green":
                html_response = f"""
                <html>
                    <head>
                        <title>Color Response</title>
                        <style>
                            body {{
                                font-family: Arial, sans-serif;
                                margin: 40px;
                            }}
                            .result-text {{
                                font-size: 16px;
                                font-weight: normal;
                            }}
                            .color-word {{
                                color: {color_value};
                                font-weight: normal;
                            }}
                        </style>
                    </head>
                    <body>
                        <p class="result-text">Your color is <span class="color-word">{color_value}</span>!</p>
                    </body>
                </html>
                """
                connectionSocket.send("HTTP/1.1 200 OK\r\n\r\n".encode())
                connectionSocket.send(html_response.encode())
                connectionSocket.close()
                return

        if requested_path == "/":
            html_content = """
            <html>
                <head>
                    <title>EE 129 Project 2</title>
                    <style>
                        body {
                            font-family: Arial, sans-serif;
                            margin: 40px;
                        }
                        h1 {
                            font-size: 36px;
                            font-weight: bold;
                        }
                        label, select, input {
                            font-size: 16px;
                        }
                        .login-btn {
                            font-size: 16px;
                            background-color: #2196F3;
                            color: white;
                            border: none;
                            padding: 8px 16px;
                            cursor: pointer;
                            margin-top: 20px;
                        }
                    </style>
                </head>
                <body>
                    <h1>EE 129 Project 2 Color Picker!</h1>
                    <form action="/" method="get">
                        <label for="color">Please choose your color:</label>
                        <select name="color" id="color">
                            <option value="green" selected>Green</option>
                            <option value="red">Red</option>
                        </select>
                        <input type="submit" value="Submit">
                    </form>
                    <form action="/login" method="get">
                        <input class="login-btn" type="submit" value="Login">
                    </form>
                </body>
            </html>
            """
            connectionSocket.send("HTTP/1.1 200 OK\r\n\r\n".encode())
            connectionSocket.send(html_content.encode())
            connectionSocket.close()
            return

        connectionSocket.send("HTTP/1.1 404 Not Found\r\n\r\n".encode())
        connectionSocket.send("<html><body><h1>404 Not Found</h1></body></html>".encode())
        connectionSocket.close()

    except Exception as e:
        connectionSocket.send("HTTP/1.1 500 Internal Server Error\r\n\r\n".encode())
        connectionSocket.send(f"<html><body><h1>Error: {e}</h1></body></html>".encode())
        connectionSocket.close()

# Main server loop: handles incoming client connections and user commands from terminal
try:
    inputs = [serverSocket, sys.stdin]  # Listen to both socket and stdin

    while True:
        print("The server is recieving at http://127.0.0.1:5500/")
        # Use select to wait for input from either:
        # - the server socket (new client connection)
        # - standard input (commands like "exit", "help")
        read_ready, _, _ = select.select(inputs, [], [])

        for source in read_ready:
            # If the server socket is ready, it means a client is trying to connect
            if source == serverSocket:
                # Accept the incoming client connection
                connectionSocket, addr = serverSocket.accept()
                # Start a new thread to handle this client independently
                # Set daemon=True so the server can exit even if client threads are running
                client_thread = threading.Thread(target=handle_client, args=(connectionSocket,), daemon=True)
                client_thread.start()
            # If input is ready on stdin, read and handle the command
            elif source == sys.stdin:
                user_input = sys.stdin.readline().strip()
                # If user types "exit", shut down the server and terminate the program
                if user_input == "exit":
                    print("Shutting down server...")
                    serverSocket.close()
                    sys.exit()
                # If user types "help", display available commands
                elif user_input == "help":
                    print("Available commands:")
                    print("  help - show this message")
                    print("  exit - shut down the server")
                # Handle unknown commands
                else:
                    print(f"{user_input}: Command Not Found")

# Handle Ctrl+C interruption (e.g., user presses Ctrl+C in terminal)
except KeyboardInterrupt:
    # Print a clean exit message
    print("\nServer interrupted. Exiting...")
    # Close the main server socket to free the port
    serverSocket.close()
    # Exit the program gracefully
    sys.exit()
