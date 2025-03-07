import os
import logging

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

    ACCESS_TOKEN_FILENAME = (
        "~/.config/ulauncher/ext_preferences/ulauncher-ticktick/access_token"
    )

    parser = StringParser()
    api = None

    def __init__(self):
        super(TickTickExtension, self).__init__()
        self.api = TickTickApi(self._read_token())
        self._init_projects()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())
        self.subscribe(ItemEnterEvent, ItemEnterEventListener())

    def _init_projects(self):
        if self.api.access_token:
            projects = self.api.get_projects()

            if projects.status_code == 200:
                self.parser.init_projects(projects.json())

    def _get_access_token_filename(self):
        return os.path.expanduser(self.ACCESS_TOKEN_FILENAME)

    def _read_token(self):
        filename = self._get_access_token_filename()
        token = ""
        if os.path.isfile(filename):
            f = open(filename, "r")
            token = f.read()
        return token

    def _write_token(self, token):
        filename = self._get_access_token_filename()
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        f = open(filename, "w")
        f.write(token)
        f.close()

    def set_access_token(self, access_token):
        self.api.access_token = access_token
        self._write_token(access_token)
        self._init_projects()

    def push(self, title, project_id, tags, adate, atime, atimezone):
        return self.api.create_task(title, project_id, tags, adate, atime, atimezone)

    def authorize(self, client_id, client_secret, port):
        access_token = AuthManager.run(client_id, client_secret, port)
        self.set_access_token(access_token)


class KeywordQueryEventListener(EventListener):

    def _prepare_description(self, tags, adate, atime, project_name):
        extracts = []
        if tags:
            extracts.append(
                "Task is tagged with " + ",".join([f"#{tag}" for tag in tags])
            )
        if adate:
            extract = f"Task is due {adate.strftime("%x")}"
            if atime:
                extract += f", {atime.strftime("%X")}"
            extracts.append(extract)
        if project_name:
            extracts.append(f"Task is stored in ~{project_name}")

        return "\n".join(extracts)

    def on_event(self, event: KeywordQueryEvent, extension: TickTickExtension):

        arg_str = event.get_argument() if event.get_argument() else ""

        items = []

        if extension.api.access_token:

            title, tags = extension.parser.extract_hashtags(arg_str)
            title, adate, atime, atimezone = extension.parser.extract_time(title)
            title, project_name, project_id = extension.parser.extract_project(title)

            desc = ""
            if len(arg_str) > 0:
                desc = self._prepare_description(tags, adate, atime, project_name)
            else:
                desc = "Type in a task title and press Enter..."

            data = {
                "action": "push",
                "title": title,
                "tags": tags,
                "date": adate,
                "time": atime,
                "timezone": atimezone,
                "project_name": project_name,
                "project_id": project_id,
            }

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

    def on_push_action(self, event: ItemEnterEvent, extension: TickTickExtension):
        data = event.get_data()
        extension.push(
            data["title"],
            data["project_id"],
            data["tags"],
            data["date"],
            data["time"],
            data["timezone"],
        )

    def on_auth_action(self, _: ItemEnterEvent, extension: TickTickExtension):
        extension.authorize(
            extension.preferences["client_id"],
            extension.preferences["client_secret"],
            extension.preferences["port"],
        )

    def on_event(self, event: ItemEnterEvent, extension: TickTickExtension):
        data = event.get_data()
        logger.info(f"Requested action \"{data['action']}\"")
        switch = {"push": self.on_push_action, "authorize": self.on_auth_action}
        switch.get(data["action"])(event, extension)


if __name__ == "__main__":
    TickTickExtension().run()
