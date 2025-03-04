import os
import logging
import requests

from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent
from ulauncher.api.shared.event import ItemEnterEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.HideWindowAction import HideWindowAction
from ulauncher.api.shared.action.OpenUrlAction import OpenUrlAction
from ulauncher.api.shared.action.ExtensionCustomAction import ExtensionCustomAction

from http.server import BaseHTTPRequestHandler
from http.server import HTTPServer

from urllib.parse import urlparse, parse_qs
from urllib.parse import urlencode

import webbrowser
import requests
import random
import string

logger = logging.getLogger(__name__)

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
        AuthData.port = port


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

    access_token = ""

    def run(client_id, client_secret, port):
    
        AuthData.client_id = client_id
        AuthData.client_secret = client_secret
        AuthData.port = int(port)

        length = 6        
        state = ''.join(random.choices(string.ascii_letters + string.digits, k=length))

        data = {
            'scope': 'tasks:write',
            'client_id': client_id,
            'state': state,
            'redirect_uri': AuthData.get_redirect_uri(),
            'response_type': 'code'
        }
        encoded_data = urlencode(data)

        auth_uri = f"https://ticktick.com/oauth/authorize?{encoded_data}"

        webbrowser.open(auth_uri)

        with HTTPServer(("127.0.0.1", AuthData.port), AuthRequestHandler) as server:
            server.handle_request()

        return AuthData.access_token
    

def read_token():
    token = ""
    if os.path.isfile("token"):
        f = open("token", "r")
        token = f.read()
    return token

def write_token(token):
    f = open("token", "w")
    f.write(token)
    f.close()


class TickTickExtension(Extension):

    def __init__(self):
        super(TickTickExtension, self).__init__()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())
        self.subscribe(ItemEnterEvent, ItemEnterEventListener())


class KeywordQueryEventListener(EventListener):

    def on_event(self, event, extension):

        access_token = read_token()
        arg_str = event.get_argument() if event.get_argument() else ""

        items = []

        if access_token:

            data = {
                "action": "push",
                "name": arg_str,
                "access_token": access_token
            }
            items.append(ExtensionResultItem(icon='images/ticktick.png',
                                            name="Create new card",
                                            description=arg_str,
                                            on_enter=ExtensionCustomAction(data)))

        else:
            client_id = extension.preferences['client_id']
            client_secret = extension.preferences['client_secret']
            if client_id and client_secret:      
                data = {
                    "action": "authorize"
                }            
                items.append(ExtensionResultItem(icon='images/ticktick.png',
                                                name='Retrieve access token',
                                                description='Click here to retrieve your access token.',
                                                on_enter=ExtensionCustomAction(data)))
            else:
                items.append(ExtensionResultItem(icon='images/ticktick.png',
                                                name='No credentials',
                                                description='Provide your credentials in this extension\'s preferences.',
                                                on_enter=HideWindowAction()))


        return RenderResultListAction(items)


class ItemEnterEventListener(EventListener):

    def push(self, title, access_token):
        url = 'https://api.ticktick.com/open/v1/task'
        payload = {
            'title': title
        }
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f"Bearer {access_token}" \
        }

        return requests.post(url, json=payload, headers=headers)

    def on_event(self, event, extension):
        data = event.get_data()
        if data['action'] == 'push':
            self.push(data['name'], data['access_token'])
        elif data['action'] == 'authorize':
            access_token = AuthManager.run(
                extension.preferences['client_id'],
                extension.preferences['client_secret'],
                extension.preferences['port']
            )
            write_token(access_token)
        

if __name__ == '__main__':
    TickTickExtension().run()
