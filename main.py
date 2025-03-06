import os
import re
import logging
import datetime

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

logger = logging.getLogger(__name__)

access_token_filename = os.path.join(
    os.path.expanduser("~"),
    ".config/ulauncher/ext_preferences/ulauncher-ticktick/access_token",
)


def read_token():
    token = ""
    if os.path.isfile(access_token_filename):
        f = open(access_token_filename, "r")
        token = f.read()
    return token


def write_token(token):
    os.makedirs(os.path.dirname(access_token_filename), exist_ok=True)
    f = open(access_token_filename, "w")
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

            data = {"action": "push", "name": arg_str, "access_token": access_token}
            items.append(
                ExtensionResultItem(
                    icon="images/ticktick.png",
                    name="Create new task",
                    description=arg_str,
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

    def push(self, str, access_token):
        api = TickTickApi(access_token)
        title, _ = self.extract_hashtags(str)
        title, date, time = self.extract_time(title)
        return api.create_task(title, date, time, str)

    def remove_match(self, match, str):
        rep = match.group(0).strip()
        return re.sub(f"( {rep}|{rep} |{rep})", "", str)

    def extract_time(self, str):
        date = None
        time = None

        # match European-style dates
        match = re.search(
            r"(?<!^\s)([0-2][0-9]|3[0-1])\.(0[0-9]|1[0-2])\.(?:(20[0-9]{2}))?(?!^\s)",
            str,
        )
        if match:
            today = datetime.date.today()
            d = int(match.group(1))
            m = int(match.group(2))
            y = int(match.group(3)) if match.group(3) else today.year
            try:
                date = datetime.date(y, m, d)

                if today > date:
                    date = datetime.date(y + 1, m, d)

                str = self.remove_match(match, str)
            except ValueError:
                logger.warning("Cannot parse date.")

        # match American-style dates
        match = re.search(
            r"(?<!^\s)(0[0-9]|1[0-2])/([0-2][0-9]|3[0-1])(?:(/20[0-9]{2}))?(?!^\s)",
            str,
        )
        if match:
            today = datetime.date.today()
            d = int(match.group(2))
            m = int(match.group(1))
            y = int(match.group(3)) if match.group(3) else today.year
            try:
                date = datetime.date(y, m, d)

                if today > date:
                    date = datetime.date(y + 1, m, d)

                str = self.remove_match(match, str)
            except ValueError:
                logger.warning("Cannot parse date.")

        # match textual today
        match = re.search(r"(?<!^\s)(today|tod)(?!^\s)", str, re.IGNORECASE)
        if match:
            date = datetime.date.today()

            str = self.remove_match(match, str)

        # match textual tomorrow
        match = re.search(r"(?<!^\s)(tomorrow|tom)(?!^\s)", str, re.IGNORECASE)
        if match:
            date = datetime.date.today() + datetime.timedelta(days=1)
            str = self.remove_match(match, str)

        # match time
        match = re.search(r"(?:\s|^)([0-1]?[0-9]|2[0-3]):([0-5][0-9])(?:\s|$)", str)
        if match:
            h = int(match.group(1))
            m = int(match.group(2))

            if not date:
                date = datetime.date.today()

            time = datetime.time(h, m)

            dt_now = datetime.datetime.now()
            dt_then = datetime.datetime(date.year, date.month, date.day, h, m, 0)

            if dt_now > dt_then:
                date = date + datetime.timedelta(days=1)

            str = self.remove_match(match, str)

        return str, date, time

    def extract_hashtags(self, str):
        textList = str.split()
        tags = []
        for i in textList:
            if i.startswith("#"):
                x = i.replace("#", "")
                tags.append(x)
                str = re.sub(f"( {i}|{i} |{i})", "", str)

        return str, tags

    def on_push_action(self, event, extension):
        data = event.get_data()
        self.push(data["name"], data["access_token"])

    def on_auth_action(self, _, extension):
        access_token = AuthManager.run(
            extension.preferences["client_id"],
            extension.preferences["client_secret"],
            extension.preferences["port"],
        )
        write_token(access_token)

    def on_event(self, event, extension):
        data = event.get_data()
        switch = {"push": self.on_push_action, "authorize": self.on_auth_action}
        switch.get(data["action"])(event, extension)


if __name__ == "__main__":
    TickTickExtension().run()
