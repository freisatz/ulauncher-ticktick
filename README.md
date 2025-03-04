# Ulauchner TickTick

A simple Ulauncher extension that allows to create tasks in TickTick.


## Setup

To authorize with your TickTick account, go to https://developer.ticktick.com/manage and select *New App*.
Specify some arbitrary *Name* and *App Service URL*. Set the field *OAuth redirect URL* to

```
http://127.0.0.1:8090
```

where the port needs to be adapted to whatever changes are made to the port in the extension preferences.

Now copy the *Client ID* and *Client secret* to the extension preferences and issue this extension from within 
Ulauncher. Click *Retrieve access token* and follow the instructions. You are now connected to your TickTick account.