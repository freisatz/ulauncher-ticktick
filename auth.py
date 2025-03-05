from http.server import BaseHTTPRequestHandler
from http.server import HTTPServer

from urllib.parse import urlparse, parse_qs

import webbrowser
import requests
import random
import string

from ticktick import TickTickApi


class AuthData:
    client_id = ""
    client_secret = ""
    port = ""
    access_token = ""

    def get_redirect_uri():
        return f"http://127.0.0.1:{AuthData.port}"

    def init(client_id, client_secret, port):
        AuthData.client_id = client_id
        AuthData.client_secret = client_secret
        AuthData.port = int(port)


class AuthRequestHandler(BaseHTTPRequestHandler):

    def fetch_token(self, code, client_id, client_secret, redirect_uri):
        response = TickTickApi.request_access_token(
            client_id, client_secret, redirect_uri, code
        )

        json = response.json()
        return json.get("access_token")

    def do_GET(self):

        # parse code from url
        parsed_url = urlparse(self.path)
        args = parse_qs(parsed_url.query)
        code = args["code"][0]

        # fetch token from api
        try:
            AuthData.access_token = self.fetch_token(
                code,
                AuthData.client_id,
                AuthData.client_secret,
                AuthData.get_redirect_uri(),
            )
            response_code = 200
            msg = "Successfully connected to your TickTick account! Continue in Ulauncher."
        except Exception as err:
            response_code = 403
            msg = f"Something went wrong:\n{err}"

        self.send_response(response_code)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(
            bytes("<html><head><title>Token creation</title></head>", "utf-8")
        )
        self.wfile.write(bytes("<body>", "utf-8"))
        self.wfile.write(bytes(f"<p>{msg}</p>", "utf-8"))
        self.wfile.write(bytes("</body></html>", "utf-8"))


class AuthManager:

    STATE_LENGTH = 6

    def generate_alphanum(length):
        return "".join(random.choices(string.ascii_letters + string.digits, k=length))

    def run(client_id, client_secret, port):

        AuthData.init(client_id, client_secret, port)

        state = AuthManager.generate_alphanum(AuthManager.STATE_LENGTH)

        auth_uri = TickTickApi.get_authorization_uri(
            AuthData.client_id, AuthData.get_redirect_uri(), state
        )

        webbrowser.open(auth_uri)

        with HTTPServer(("127.0.0.1", AuthData.port), AuthRequestHandler) as server:
            server.handle_request()

        return AuthData.access_token
