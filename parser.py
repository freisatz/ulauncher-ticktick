import datetime
import re
import logging

logger = logging.getLogger(__name__)


class StringParser:

    projects_dict = dict()

    def _remove_from_str(self, search, str):
        rep = search.strip()
        return re.sub(f"( {rep}|{rep} |{rep})", "", str)

    def init_projects(self, project_array):
        for project in project_array:
            self.projects_dict[project["name"].lower()] = (
                project["id"],
                project["name"],
            )

    def extract_project(self, str):
        project_names = []
        project_name = ""
        project_id = ""
        for name in self.projects_dict.keys():
            project_names.append(name)

        match = re.search(
            r"(?<![^\s])~(" + "|".join(project_names) + r")",
            str,
            re.IGNORECASE,
        )
        if match:
            project_key = match.group(1).lower()
            project_id, project_name = self.projects_dict.get(project_key)
            str = self._remove_from_str(match.group(0), str)
        return str, project_name, project_id

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
        target_names = dict()
        target_names["jan"] = 1
        target_names["feb"] = 2
        target_names["mar"] = 3
        target_names["apr"] = 4
        target_names["may"] = 5
        target_names["jun"] = 6
        target_names["jul"] = 7
        target_names["aug"] = 8
        target_names["sep"] = 9
        target_names["oct"] = 10
        target_names["nov"] = 11
        target_names["dec"] = 12
        target_names["january"] = 1
        target_names["february"] = 2
        target_names["march"] = 3
        target_names["april"] = 4
        target_names["may"] = 5
        target_names["june"] = 6
        target_names["july"] = 7
        target_names["august"] = 8
        target_names["september"] = 9
        target_names["october"] = 10
        target_names["november"] = 11
        target_names["december"] = 12

        month_string = "|".join(target_names.keys())
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
            m = target_names[match.group(1).lower()]
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

        # match textual next week|month|year
        # match textual month
        target_names = dict()
        target_names["wk"] = 1
        target_names["mon"] = 2
        target_names["yr"] = 3
        target_names["week"] = 1
        target_names["month"] = 2
        target_names["year"] = 3

        match = re.search(
            r"(?<![^\s])next\s+(" + "|".join(target_names.keys()) + r")(?![^\s])",
            str,
            re.IGNORECASE,
        )
        if match:
            key = target_names.get(match.group(1))
            if key == 1:
                date = datetime.date.today()
                days = 7 - date.weekday()
                date = date + datetime.timedelta(days=days)
            elif key == 2:
                date = datetime.date.today()
                date = datetime.date(
                    date.year if date.month < 12 else date.year + 1,
                    date.month % 12 + 1,
                    1,
                )
            elif key == 3:
                date = datetime.date.today()
                date = datetime.date(date.year + 1, 1, 1)

            str = self._remove_from_str(match.group(0), str)

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

    def extract_hashtags(self, string):
        text_list = string.split()
        tags = []
        p = r"^#([\w\-_]+)$"
        for i in text_list:
            match = re.search(p, i)
            if match:
                tags.append(match.group(1))
                string = self._remove_from_str(match.group(0), string)

        return string, tags

    def extract_priority(self, string):

        priority_dict = {
            "low": "low",
            "l": "low",
            "medium": "medium",
            "m": "medium",
            "high": "high",
            "h": "high",
        }

        priority = ""
        p = r"(?<![^\s])!(low|medium|high|l|m|h)(?![^\s])"

        match = re.search(p, string, re.IGNORECASE)
        if match:
            priority = priority_dict.get(match.group(1).lower(), "")
            string = self._remove_from_str(match.group(0), string)

        return string, priority

    def get_project_suggestions(self, arg_str, max_matches=0):
        projects = []
        num_matches = 0
        arg_len = len(arg_str)

        match = re.search(r"(?<![^\s])~([\w_\- ]*)$", arg_str, re.IGNORECASE)

        if match:
            search = match.group(1)
            base = arg_str[0 : arg_len - len(search) - 1]
            for project in self.projects_dict.values():
                if len(search) < len(project[1]) and re.match(
                    search, project[1], re.IGNORECASE
                ):
                    projects.append(project[1])
                    num_matches += 1
                    if num_matches == max_matches:
                        break

            return base, projects

        return arg_str, []

    def get_priority_suggestions(self, arg_str, max_matches=0):
        priorities = []
        num_matches = 0
        arg_len = len(arg_str)

        match = re.search(r"(?<![^\s])!(\w{0,6})$", arg_str, re.IGNORECASE)

        if match:
            search = match.group(1)
            base = arg_str[0 : arg_len - len(search) - 1]
            for priority in ["low", "medium", "high"]:
                if len(search) < len(priority) and re.match(
                    search, priority, re.IGNORECASE
                ):
                    priorities.append(priority)
                    num_matches += 1
                    if num_matches == max_matches:
                        break

            return base, priorities

        return arg_str, []
