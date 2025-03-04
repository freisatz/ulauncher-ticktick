
from http.server import BaseHTTPRequestHandler
from http.server import HTTPServer

from urllib.parse import urlencode, urlparse, parse_qs

import webbrowser
import requests
import random
import string

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
        url = 'https://ticktick.com/oauth/token'

        payload = {
            'code': code,
            'grant_type': 'authorization_code',
            'scope': 'tasks:write',
            'redirect_uri': redirect_uri
        }
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        response = requests.post(url, data=urlencode(payload), headers=headers, auth=(client_id, client_secret))

        json = response.json()
        return json.get("access_token")

    def do_GET(self):

        # parse code from url
        parsed_url = urlparse(self.path)
        args = parse_qs(parsed_url.query)
        code = args['code'][0]

        # fetch token from api

        response_code = 403
        msg = "Continue in Ulauncher."

        try:
            AuthData.access_token = self.fetch_token(
                code,
                AuthData.client_id,
                AuthData.client_secret,
                AuthData.get_redirect_uri()
            )
            response_code = 200
            msg = "Continue in Ulauncher."
        except Exception as err:
            response_code = 200
            msg = f"Something went wrong:\n{err}"

        self.send_response(response_code)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(bytes("<html><head><title>Token creation</title></head>", "utf-8"))
        self.wfile.write(bytes("<body>", "utf-8"))
        self.wfile.write(bytes(f"<p>{msg}</p>", "utf-8"))
        self.wfile.write(bytes("</body></html>", "utf-8"))


class AuthManager:

    STATE_LENGTH = 6

    def generate_alphanum(length):        
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    
    def get_authorization_uri(client_id, redirect_uri, state):

        data = {
            'scope': 'tasks:write',
            'client_id': client_id,
            'state': state,
            'redirect_uri': redirect_uri,
            'response_type': 'code'
        }
        encoded_data = urlencode(data)

        return f"https://ticktick.com/oauth/authorize?{encoded_data}"

    def run(client_id, client_secret, port):
    
        AuthData.init(client_id, client_secret, port)
      
        state = AuthManager.generate_alphanum(AuthManager.STATE_LENGTH)

        auth_uri = AuthManager.get_authorization_uri(
            AuthData.client_id, 
            AuthData.get_redirect_uri(),
            state
        )

        webbrowser.open(auth_uri)

        with HTTPServer(("127.0.0.1", AuthData.port), AuthRequestHandler) as server:
            server.handle_request()

        return AuthData.access_token
    
