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


class TickTickExtension(Extension):

    access_token_filename = os.path.expanduser(
        "~/.config/ulauncher/ext_preferences/ulauncher-ticktick/access_token"
    )

    def __init__(self):
        super(TickTickExtension, self).__init__()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())
        self.subscribe(ItemEnterEvent, ItemEnterEventListener())

    def read_token(self):
        token = ""
        if os.path.isfile(self.access_token_filename):
            f = open(self.access_token_filename, "r")
            token = f.read()
        return token

    def write_token(self, token):
        os.makedirs(os.path.dirname(self.access_token_filename), exist_ok=True)
        f = open(self.access_token_filename, "w")
        f.write(token)
        f.close()


class KeywordQueryEventListener(EventListener):

    def on_event(self, event, extension: TickTickExtension):

        access_token = extension.read_token()
        arg_str = event.get_argument() if event.get_argument() else ""

        items = []

        if access_token:
            desc = ""
            if len(arg_str) == 0:
                desc = "Type in a task title and press Enter..."
            data = {"action": "push", "name": arg_str, "access_token": access_token}
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

    def push(self, str, access_token):
        api = TickTickApi(access_token)
        title, _ = self._extract_hashtags(str)
        title, adate, atime, atimezone = self._extract_time(title)
        return api.create_task(title, str, adate, atime, atimezone)

    def _remove_match(self, match, str):
        rep = match.group(0).strip()
        return re.sub(f"( {rep}|{rep} |{rep})", "", str)

    def _extract_time(self, str):
        date = None
        time = None

        # match European-style dates DD.MM[.YYYY]
        match = re.search(
            r"(?<!^\s)([0-2][0-9]|3[0-1])\.(0[0-9]|1[0-2])\.(?:((?:20)?[0-9]{2}))?(?!^\s)",
            str,
        )
        if match:
            today = datetime.date.today()
            d = int(match.group(1))
            m = int(match.group(2))
            y = match.group(3)
            try:

                if not y:
                    y = today.year
                    date = datetime.date(y, m, d)
                    if today > date:
                        date = datetime.date(y + 1, m, d)
                else:
                    y = int(y)
                    if int(y) < 100:
                        y = int(y) + 2000
                    date = datetime.date(y, m, d)

                str = self._remove_match(match, str)
            except ValueError:
                logger.warning("Cannot parse date.")

        # match American-style dates MM/DD[/YYYY]
        match = re.search(
            r"(?<!^\s)(0[0-9]|1[0-2])/([0-2][0-9]|3[0-1])(?:(?:/)((?:20)?[0-9]{2}))?(?!^\s)",
            str,
        )
        if match:
            today = datetime.date.today()
            d = int(match.group(2))
            m = int(match.group(1))
            y = match.group(3)
            try:
                if not y:
                    y = today.year
                    date = datetime.date(y, m, d)
                    if today > date:
                        date = datetime.date(y + 1, m, d)
                else:
                    y = int(y)
                    if int(y) < 100:
                        y = int(y) + 2000
                    date = datetime.date(y, m, d)

                str = self._remove_match(match, str)
            except ValueError:
                logger.warning("Cannot parse date.")

        # match Unix-style dates YYYY-MM-DD
        match = re.search(
            r"(?<!^\s)(20[0-9]{2})-(0[0-9]|1[0-2])-([0-2][0-9]|3[0-1])(?!^\s)",
            str,
        )
        if match:
            d = int(match.group(3))
            m = int(match.group(2))
            y = int(match.group(1))
            try:
                date = datetime.date(y, m, d)

                str = self._remove_match(match, str)
            except ValueError:
                logger.warning("Cannot parse date.")

        # match textual month
        month_names = dict()
        month_names["jan"] = 1
        month_names["feb"] = 2
        month_names["mar"] = 3
        month_names["apr"] = 4
        month_names["may"] = 5
        month_names["jun"] = 6
        month_names["jul"] = 7
        month_names["aug"] = 8
        month_names["sep"] = 9
        month_names["oct"] = 10
        month_names["nov"] = 11
        month_names["dec"] = 12
        month_names["january"] = 1
        month_names["february"] = 2
        month_names["march"] = 3
        month_names["april"] = 4
        month_names["may"] = 5
        month_names["june"] = 6
        month_names["july"] = 7
        month_names["august"] = 8
        month_names["september"] = 9
        month_names["october"] = 10
        month_names["november"] = 11
        month_names["december"] = 12

        month_string = "|".join(month_names.keys())
        match = re.search(
            r"(?<!^\s)("
            + month_string
            + r")(?:\.)?(?:\s+([0-2]?[0-9]|3[0-1])(?:(?:th|rd|st|\.))?(?:\s+((?:20)?[0-9]{2}))?)?(?!^\s)",
            str,
            re.IGNORECASE,
        )
        if match:
            today = datetime.date.today()
            d = match.group(2)
            m = month_names[match.group(1).lower()]
            y = match.group(3)
            try:
                if not d:
                    d = 1
                else:
                    d = int(d)

                if not y:
                    y = today.year
                    date = datetime.date(y, m, d)
                    if today > date:
                        date = datetime.date(y + 1, m, d)

                else:
                    y = int(y)
                    if int(y) < 100:
                        y = int(y) + 2000
                    date = datetime.date(y, m, d)

                str = self._remove_match(match, str)
            except ValueError:
                logger.warning("Cannot parse date.")

        # match textual to[day]
        match = re.search(r"(?<!^\s)(today|tod)(?!^\s)", str, re.IGNORECASE)
        if match:
            date = datetime.date.today()

            str = self._remove_match(match, str)

        # match textual to[morrow]
        match = re.search(r"(?<!^\s)(tomorrow|tom)(?!^\s)", str, re.IGNORECASE)
        if match:
            date = datetime.date.today() + datetime.timedelta(days=1)
            str = self._remove_match(match, str)

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

            str = self._remove_match(match, str)

        tz_string = datetime.datetime.now(datetime.timezone.utc).astimezone().tzname()

        return str, date, time, tz_string

    def _extract_hashtags(self, str):
        textList = str.split()
        tags = []
        for i in textList:
            if i.startswith("#"):
                x = i.replace("#", "")
                tags.append(x)
                str = re.sub(f"( {i}|{i} |{i})", "", str)

        return str, tags

    def on_push_action(self, event, _):
        data = event.get_data()
        self.push(data["name"], data["access_token"])

    def on_auth_action(self, _, extension: TickTickExtension):
        access_token = AuthManager.run(
            extension.preferences["client_id"],
            extension.preferences["client_secret"],
            extension.preferences["port"],
        )
        extension.write_token(access_token)

    def on_event(self, event, extension):
        data = event.get_data()
        switch = {"push": self.on_push_action, "authorize": self.on_auth_action}
        switch.get(data["action"])(event, extension)


if __name__ == "__main__":
    TickTickExtension().run()
