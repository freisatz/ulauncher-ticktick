import datetime
import re
import logging

logger = logging.getLogger(__name__)


class StringParser:

    def _remove_from_str(self, search, str):
        rep = search.strip()
        return re.sub(f"( {rep}|{rep} |{rep})", "", str)

    def extract_time(self, str):
        date = None
        time = None

        # match European-style dates DD.MM[.YYYY]
        match = re.search(
            r"(?<![^\s])([0-2][0-9]|3[0-1])\.(0[0-9]|1[0-2])\.(?:((?:20)?[0-9]{2}))?(?![^\s])",
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

                str = self._remove_from_str(match.group(0), str)
            except ValueError:
                logger.warning("Cannot parse date.")

        # match American-style dates MM/DD[/YYYY]
        match = re.search(
            r"(?<![^\s])(0[0-9]|1[0-2])/([0-2][0-9]|3[0-1])(?:(?:/)((?:20)?[0-9]{2}))?(?![^\s])",
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

                str = self._remove_from_str(match.group(0), str)
            except ValueError:
                logger.warning("Cannot parse date.")

        # match ISO-style dates YYYY-MM-DD
        match = re.search(
            r"(?<![^\s])(20[0-9]{2})-(0[0-9]|1[0-2])-([0-2][0-9]|3[0-1])(?![^\s])",
            str,
        )
        if match:
            d = int(match.group(3))
            m = int(match.group(2))
            y = int(match.group(1))
            try:
                date = datetime.date(y, m, d)

                str = self._remove_from_str(match.group(0), str)
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
            r"(?<![^\s])("
            + month_string
            + r")(?:\.)?(?:\s+([0-2]?[0-9]|3[0-1])(?:(?:th|rd|st|\.))?(?:\s+((?:20)?[0-9]{2}))?)?(?![^\s])",
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

                str = self._remove_from_str(match.group(0), str)
            except ValueError:
                logger.warning("Cannot parse date.")

        # match textual to[day]
        match = re.search(r"(?<![^\s])(today|tod)(?![^\s])", str, re.IGNORECASE)
        if match:
            date = datetime.date.today()

            str = self._remove_from_str(match.group(0), str)

        # match textual to[morrow]
        match = re.search(r"(?<![^\s])(tomorrow|tom)(?![^\s])", str, re.IGNORECASE)
        if match:
            date = datetime.date.today() + datetime.timedelta(days=1)
            str = self._remove_from_str(match.group(0), str)

        # match time
        match = re.search(r"(?<![^\s])([0-1]?[0-9]|2[0-3]):([0-5][0-9])(?![^\s])", str)
        if match:
            h = int(match.group(1))
            m = int(match.group(2))

            if not date:
                date = datetime.date.today()

                dt_now = datetime.datetime.now()
                dt_then = datetime.datetime(date.year, date.month, date.day, h, m)

                if dt_now > dt_then:
                    date = date + datetime.timedelta(days=1)

            time = datetime.time(h, m)
            str = self._remove_from_str(match.group(0), str)

        tz_string = datetime.datetime.now(datetime.timezone.utc).astimezone().tzname()

        return str, date, time, tz_string

    def extract_hashtags(self, str):
        text_list = str.split()
        tags = []
        p = r"^#([a-zA-Z0-9-_]+)$"
        for i in text_list:
            match = re.search(p, i)
            if match:
                tags.append(match.group(1))
                str = self._remove_from_str(match.group(0), str)

        return str, tags
