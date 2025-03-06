import requests
import datetime
import pytz
import time

from urllib.parse import urlencode


class TickTickApi:

    access_token = ""

    def __init__(self, access_token=""):
        self.access_token = access_token

    def create_task(self, title, adate, atime, desc):

        url = "https://api.ticktick.com/open/v1/task"

        reminders = []
        formatted_date = ""
        isAllDay = False

        tz_name, _ = time.tzname
        timezone = pytz.timezone(tz_name)

        if adate:

            if atime:
                dt = datetime.datetime(
                    adate.year,
                    adate.month,
                    adate.day,
                    atime.hour,
                    atime.minute,
                    atime.second,
                )
                reminders.append("TRIGGER:PT0S")
            else:
                dt = datetime.datetime(adate.year, adate.month, adate.day)
                isAllDay = True

        offset = timezone.localize(dt).utcoffset()

        offset_sign = "-" if offset.seconds < 0 else "+"
        offset_hours = str(int(offset.seconds // 3600)).zfill(2)
        offset_minutes = str(int(offset.seconds // 60) % 60).zfill(2)

        formatted_date = f"{dt.isoformat()}{offset_sign}{offset_hours}{offset_minutes}"

        print(formatted_date)

        payload = {
            "title": title,
            "dueDate": formatted_date,
            "isAllDay": isAllDay,
            "reminders": reminders,
            "desc": desc,
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}",
        }

        # strftime("%Y-%m-%dT%H:%M:S")

        return requests.post(url, json=payload, headers=headers)

    def get_authorization_uri(client_id, redirect_uri, state):

        data = {
            "scope": "tasks:write",
            "client_id": client_id,
            "state": state,
            "redirect_uri": redirect_uri,
            "response_type": "code",
        }
        encoded_data = urlencode(data)

        return f"https://ticktick.com/oauth/authorize?{encoded_data}"

    def request_access_token(client_id, client_secret, redirect_uri, code):
        url = "https://ticktick.com/oauth/token"

        payload = {
            "code": code,
            "grant_type": "authorization_code",
            "scope": "tasks:write",
            "redirect_uri": redirect_uri,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        return requests.post(
            url,
            data=urlencode(payload),
            headers=headers,
            auth=(client_id, client_secret),
        )
