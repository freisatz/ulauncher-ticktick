import os
import logging
import re

from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent
from ulauncher.api.shared.event import ItemEnterEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.HideWindowAction import HideWindowAction
from ulauncher.api.shared.action.ExtensionCustomAction import ExtensionCustomAction

from auth import AuthManager
from ticktick import TickTickApi
from parser import StringParser

logger = logging.getLogger(__name__)


class TickTickExtension(Extension):

    access_token_filename = os.path.expanduser(
        "~/.config/ulauncher/ext_preferences/ulauncher-ticktick/access_token"
    )
    api = None

    parser = StringParser()
    project_dicts = dict()

    def __init__(self):
        super(TickTickExtension, self).__init__()
        self.api = TickTickApi(self._read_token())
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())
        self.subscribe(ItemEnterEvent, ItemEnterEventListener())

    def _init_projects(self, access_token):
        api = TickTickApi(access_token)
        projects = api.get_projects()

        if projects.status_code == 200:
            json = projects.json()
            for project in json:
                self.projects_dict[project["name"]] = project["id"]

    def _read_token(self):
        token = ""
        if os.path.isfile(self.access_token_filename):
            f = open(self.access_token_filename, "r")
            token = f.read()
        return token

    def _write_token(self, token):
        os.makedirs(os.path.dirname(self.access_token_filename), exist_ok=True)
        f = open(self.access_token_filename, "w")
        f.write(token)
        f.close()

    def set_access_token(self, access_token):
        self.api.access_token = access_token
        self._write_token(access_token)

    def push(self, str):
        title, tags = self.parser.extract_hashtags(str)
        title, adate, atime, atimezone = self.parser.extract_time(title)
        return self.api.create_task(title, tags, adate, atime, atimezone)


class KeywordQueryEventListener(EventListener):

    def on_event(self, event, extension: TickTickExtension):

        arg_str = event.get_argument() if event.get_argument() else ""

        items = []

        if extension.api.access_token:
            desc = ""
            if len(arg_str) == 0:
                desc = "Type in a task title and press Enter..."
            data = {"action": "push", "name": arg_str}
            items.append(
                ExtensionResultItem(
                    icon="images/ticktick.png",
                    name="Create new task",
                    description=desc,
                    on_enter=ExtensionCustomAction(data),
                )
            )

        else:
            client_id = extension.preferences["client_id"]
            client_secret = extension.preferences["client_secret"]
            if client_id and client_secret:
                data = {"action": "authorize"}
                items.append(
                    ExtensionResultItem(
                        icon="images/ticktick.png",
                        name="Retrieve access token",
                        description="Click here to retrieve your access token.",
                        on_enter=ExtensionCustomAction(data),
                    )
                )
            else:
                items.append(
                    ExtensionResultItem(
                        icon="images/ticktick.png",
                        name="No credentials",
                        description="Provide your credentials in this extension's preferences.",
                        on_enter=HideWindowAction(),
                    )
                )

        return RenderResultListAction(items)


class ItemEnterEventListener(EventListener):

    def on_push_action(self, event, extension):
        data = event.get_data()
        extension.push(data["name"])

    def on_auth_action(self, _, extension: TickTickExtension):
        access_token = AuthManager.run(
            extension.preferences["client_id"],
            extension.preferences["client_secret"],
            extension.preferences["port"],
        )
        extension.set_access_token(access_token)

    def on_event(self, event, extension):
        data = event.get_data()
        logger.info(f"Requested action \"{data['action']}\"")
        switch = {"push": self.on_push_action, "authorize": self.on_auth_action}
        switch.get(data["action"])(event, extension)


if __name__ == "__main__":
    TickTickExtension().run()
