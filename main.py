import os
import logging

from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent
from ulauncher.api.shared.event import ItemEnterEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.item.ExtensionSmallResultItem import ExtensionSmallResultItem
from ulauncher.api.shared.action.SetUserQueryAction import SetUserQueryAction
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.DoNothingAction import DoNothingAction
from ulauncher.api.shared.action.HideWindowAction import HideWindowAction
from ulauncher.api.shared.action.ExtensionCustomAction import ExtensionCustomAction

from auth import AuthManager
from ticktick import TickTickApi
from parser import StringParser
from variable import Variable, VariableUpdateListener

logger = logging.getLogger(__name__)


class TickTickExtension(Extension, VariableUpdateListener):

    ACCESS_TOKEN_FILENAME = (
        "~/.config/ulauncher/ext_preferences/ulauncher-ticktick/access_token"
    )

    access_token = Variable()

    def __init__(self):
        super(TickTickExtension, self).__init__()

        itemEnterEventListener = ItemEnterEventListener()
        keywordQueryEventListener = KeywordQueryEventListener()

        self.access_token.subscribe(itemEnterEventListener)
        self.access_token.subscribe(keywordQueryEventListener)

        self.access_token.set(self._read_access_token())

        self.access_token.subscribe(self)

        self.subscribe(KeywordQueryEvent, keywordQueryEventListener)
        self.subscribe(ItemEnterEvent, itemEnterEventListener)

    def _get_access_token_filename(self):
        return os.path.expanduser(self.ACCESS_TOKEN_FILENAME)

    def _read_access_token(self):
        filename = self._get_access_token_filename()
        access_token = ""
        if os.path.isfile(filename):
            logger.debug(f'Read access token from "{filename}"')
            f = open(filename, "r")
            access_token = f.read()
        return access_token

    def _write_access_token(self, access_token):
        filename = self._get_access_token_filename()
        logger.debug(f'Write access token to "{filename}"')
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        f = open(filename, "w")
        f.write(access_token)
        f.close()

    def on_update(self, value):
        self._write_access_token(value)

    def get_access_token(self):
        return self.access_token.get()

    def set_access_token(self, access_token):
        self.access_token.set(access_token)


class KeywordQueryEventListener(EventListener, VariableUpdateListener):

    api = None
    parser = None

    def __init__(self):
        super().__init__()
        self.api = TickTickApi()
        self.parser = StringParser()

    def _compile_description(self, tags, priority, adate, atime, project_name):
        extracts = []
        if tags:
            extracts.append("tag with " + ",".join([f"#{tag}" for tag in tags]))
        if priority:
            extracts.append(f"set priority to {priority}")
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

    def on_update(self, value):
        self.api.access_token = value

        if value:
            response = self.api.get_projects()

            if response.ok:
                self.parser.init_projects(response.json())

    def on_event(self, event: KeywordQueryEvent, extension: TickTickExtension):

        arg_str = event.get_argument() if event.get_argument() else ""

        items = []

        if extension.get_access_token():

            # add project name suggestions item
            base, suggestions = self.parser.get_project_suggestions(
                event.get_query(), max_matches=10
            )

            for suggestion in suggestions:

                items.append(
                    ExtensionSmallResultItem(
                        icon="images/ticktick.png",
                        name=f"~{suggestion}",
                        description="",
                        on_enter=SetUserQueryAction(f"{base}~{suggestion} "),
                    )
                )

            # add priority suggestions item
            base, suggestions = self.parser.get_priority_suggestions(event.get_query())

            for suggestion in suggestions:

                items.append(
                    ExtensionSmallResultItem(
                        icon="images/ticktick.png",
                        name=f"!{suggestion}",
                        description="",
                        on_enter=SetUserQueryAction(f"{base}!{suggestion} "),
                    )
                )

            if not len(items):
                # add item "Create new task"
                title, tags = self.parser.extract_hashtags(arg_str)
                title, priority = self.parser.extract_priority(title)
                title, adate, atime, atimezone = self.parser.extract_time(title)
                title, project_name, project_id = self.parser.extract_project(title)

                desc = ""
                action = None
                if len(title) > 0:
                    desc = self._compile_description(
                        tags, priority, adate, atime, project_name
                    )
                    priority_dict = {"low": 1, "medium": 2, "high": 3}

                    data = {
                        "action": "create",
                        "title": title,
                        "tags": tags,
                        "priority": priority_dict.get(priority, 0),
                        "date": adate,
                        "time": atime,
                        "timezone": atimezone,
                        "project_name": project_name,
                        "project_id": project_id,
                    }

                    action = ExtensionCustomAction(data)
                else:
                    desc = "Type in a task title and press Enter..."
                    action = DoNothingAction()

                items.append(
                    ExtensionResultItem(
                        icon="images/ticktick.png",
                        name="Create new task",
                        description=desc,
                        on_enter=action,
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


class ItemEnterEventListener(EventListener, VariableUpdateListener):

    api = TickTickApi()

    def __init__(self):
        super().__init__()

    def _do_create(self, event: ItemEnterEvent, _: TickTickExtension):
        data = event.get_data()
        self.api.create_task(
            data["title"],
            data["project_id"],
            data["tags"],
            data["priority"],
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
        extension.set_access_token(access_token)

    def on_update(self, value):
        self.api.access_token = value

    def on_event(self, event: ItemEnterEvent, extension: TickTickExtension):
        action = event.get_data().get("action")
        logger.info(f'Requested action "{action}"')
        switch = {"create": self._do_create, "authorize": self._do_authorize}
        switch.get(action)(event, extension)


if __name__ == "__main__":
    TickTickExtension().run()
