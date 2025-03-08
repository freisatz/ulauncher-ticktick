import os
import logging

from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent
from ulauncher.api.shared.event import ItemEnterEvent
from ulauncher.api.shared.event import PreferencesEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.HideWindowAction import HideWindowAction
from ulauncher.api.shared.action.ExtensionCustomAction import ExtensionCustomAction

from auth import AuthManager
from ticktick import TickTickApi
from parser import StringParser

logger = logging.getLogger(__name__)


class AccessTokenListener:

    def on_update(self, access_token):
        pass


class AccessTokenManager:

    ACCESS_TOKEN_FILENAME = (
        "~/.config/ulauncher/ext_preferences/ulauncher-ticktick/access_token"
    )

    access_token = ""
    is_updated = False

    listeners = []

    def _get_access_token_filename(self):
        return os.path.expanduser(self.ACCESS_TOKEN_FILENAME)

    def _read_from_file(self):
        filename = self._get_access_token_filename()
        token = ""
        if os.path.isfile(filename):
            f = open(filename, "r")
            token = f.read()
        return token

    def _write_to_file(self, token):
        filename = self._get_access_token_filename()
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        f = open(filename, "w")
        f.write(token)
        f.close()

    def _update(self, access_token):
        self.access_token = access_token
        self.is_updated = True
        for listener in self.listeners:
            listener.on_update(access_token)

    def init(self):
        if not self.is_updated:
            self._update(self._read_from_file())

    def get(self):
        self.init()
        return self.access_token

    def set(self, access_token):
        if self.access_token != access_token:
            self._write_to_file(access_token)
            self._update(access_token)

    def subscribe(self, listener):
        self.listeners.append(listener)


class TickTickExtension(Extension):

    access_token_mgr = AccessTokenManager()
    
    def __init__(self):
        super(TickTickExtension, self).__init__()

        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener(self.access_token_mgr))
        self.subscribe(ItemEnterEvent, ItemEnterEventListener(self.access_token_mgr))
        self.subscribe(PreferencesEvent, PreferencesEventListener())


class KeywordQueryEventListener(EventListener):

    api = None
    parser = None

    def __init__(self, access_token_mgr):
        super().__init__()
        self.api = TickTickApi()
        self.parser = StringParser()

        access_token_mgr.subscribe(self)

    def _compile_description(self, tags, adate, atime, project_name):
        extracts = []
        if tags:
            extracts.append("tag with " + ",".join([f"#{tag}" for tag in tags]))
        if adate:
            extract = f"set due date to {adate.strftime("%x")}"
            if atime:
                extract += f", {atime.strftime("%X")}"
            extracts.append(extract)
        if project_name:
            extracts.append(f"store in ~{project_name}")

        result = ""

        if len(extracts) > 0:
            last = extracts.pop()
            if len(extracts) > 0:
                result = ", ".join(extracts)
                result += " and "
            result += last
            result = f"{result[0].upper()}{result[1:]}."

        return result

    def on_update(self, access_token):
        self.api.access_token = access_token

        response = self.api.get_projects()

        if response.ok:
            self.parser.init_projects(response.json())

    def on_event(self, event: KeywordQueryEvent, extension: TickTickExtension):

        arg_str = event.get_argument() if event.get_argument() else ""

        items = []

        if extension.access_token_mgr.get():

            # add item "Create new task"
            title, tags = self.parser.extract_hashtags(arg_str)
            title, adate, atime, atimezone = self.parser.extract_time(title)
            title, project_name, project_id = self.parser.extract_project(title)

            desc = ""
            if len(arg_str) > 0:
                desc = self._compile_description(tags, adate, atime, project_name)
            else:
                desc = "Type in a task title and press Enter..."

            data = {
                "action": "create",
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
                # add item "Retrieve access token"
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
                # add item "No credentials"
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

    api = TickTickApi()

    def __init__(self, access_token_mgr):
        super().__init__()
        access_token_mgr.subscribe(self)

    def _do_create(self, event: ItemEnterEvent, _: TickTickExtension):
        data = event.get_data()
        self.api.create_task(
            data["title"],
            data["project_id"],
            data["tags"],
            data["date"],
            data["time"],
            data["timezone"],
        )

    def _do_authorize(self, _: ItemEnterEvent, extension: TickTickExtension):
        access_token = AuthManager.run(
            extension.preferences["client_id"],
            extension.preferences["client_secret"],
            extension.preferences["port"],
        )
        extension.access_token_mgr.set(access_token)

    def on_update(self, access_token):
        self.api.access_token = access_token

    def on_event(self, event: ItemEnterEvent, extension: TickTickExtension):
        data = event.get_data()
        logger.info(f"Requested action \"{data['action']}\"")
        switch = {"create": self._do_create, "authorize": self._do_authorize}
        switch.get(data["action"])(event, extension)


class PreferencesEventListener(EventListener):

    def __init__(self):
        super().__init__()

    def on_event(self, _:PreferencesEvent, extension : TickTickExtension):
        extension.access_token_mgr.init()


if __name__ == "__main__":
    TickTickExtension().run()
