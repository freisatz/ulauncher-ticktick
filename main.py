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

from auth import AuthManager

logger = logging.getLogger(__name__)

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
