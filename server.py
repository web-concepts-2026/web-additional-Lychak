import socket
import json
import os

HOST = "localhost"
PORT = 8080

items = []


def parse_request(data):
    head, _, body = data.partition("\r\n\r\n")
    lines = head.split("\r\n")

    method, full_path, version = lines[0].split(" ")

    headers = {}
    for line in lines[1:]:
        name, _, value = line.partition(":")
        headers[name.strip()] = value.strip()

    path, _, query_string = full_path.partition("?")
    query = {}
    if query_string:
        for pair in query_string.split("&"):
            key, _, value = pair.partition("=")
            query[key] = value

    return method, path, query, headers, body


def make_response(status, body, content_type="text/html"):
    if isinstance(body, str):
        body = body.encode()
    head = f"HTTP/1.1 {status}\r\n"
    head += f"Content-Type: {content_type}\r\n"
    head += f"Content-Length: {len(body)}\r\n"
    head += "Connection: close\r\n\r\n"
    return head.encode() + body


def handle_get(path, query):
    if path == "/page":
        page_id = query.get("id", "none")
        return make_response("200 OK", f"<h1>Page {page_id}</h1><p>Query: {query}</p>")

    if path == "/items":
        return make_response("200 OK", json.dumps(items), "application/json")

    if path == "/":
        path = "/index.html"

    file_path = "static" + path
    if not os.path.isfile(file_path):
        return make_response("404 Not Found", "<h1>404 Not Found</h1>")

    with open(file_path, "rb") as f:
        content = f.read()

    if file_path.endswith(".css"):
        content_type = "text/css"
    else:
        content_type = "text/html"
    return make_response("200 OK", content, content_type)


def handle_post(path, headers, body):
    if headers.get("Content-Type") != "application/json":
        return make_response("400 Bad Request", "Content-Type must be application/json")

    data = json.loads(body)

    if path == "/items":
        items.append(data)
        return make_response("201 Created", json.dumps({"added": data}), "application/json")

    return make_response("200 OK", json.dumps({"received": data}), "application/json")


def handle_client(conn):
    data = conn.recv(4096).decode()
    if not data:
        conn.close()
        return

    method, path, query, headers, body = parse_request(data)

    length = int(headers.get("Content-Length", 0))
    while len(body.encode()) < length:
        body += conn.recv(4096).decode()

    print(method, path, query)
    print(headers)
    if body:
        print(body)

    if method == "GET":
        response = handle_get(path, query)
    elif method == "POST":
        response = handle_post(path, headers, body)
    else:
        response = make_response("405 Method Not Allowed", "Method Not Allowed")

    conn.sendall(response)
    conn.close()


server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind((HOST, PORT))
server.listen(5)
print(f"Server running on http://{HOST}:{PORT}", flush=True)

while True:
    conn, addr = server.accept()
    handle_client(conn)
