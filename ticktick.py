import requests
import datetime
import pytz

from urllib.parse import urlencode


class TickTickApi:

    access_token = ""

    def __init__(self, access_token=""):
        self.access_token = access_token

    def create_task(self, title, desc, adate, atime, atimezone):

        reminders = []
        isAllDay = False
        formatted_date = ""

        if adate:

            adatetime = None

            if atime:
                adatetime = datetime.datetime(
                    adate.year,
                    adate.month,
                    adate.day,
                    atime.hour,
                    atime.minute,
                    atime.second,
                )
                reminders.append("TRIGGER:PT0S")
            else:
                adatetime = datetime.datetime(adate.year, adate.month, adate.day)
                isAllDay = True

            adatetime = pytz.timezone(atimezone).localize(adatetime)

            formatted_date = adatetime.strftime("%Y-%m-%dT%H:%M:%S%z")

        print(formatted_date)

        url = "https://api.ticktick.com/open/v1/task"
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
