# webserver_monitor
A long running process that monitors webserver urls

## Installation
This program uses only the standard python 3 distribution and does not require any package installation.

## Configuration
The program is configured with four handlers by default at the bottom of method `main()`:
- Handler: logs to console. 
CONFIGURATION: none.
- DBHandler: logs all responses that aren't HTTP status code 200 to a Sqlite3 database. 
CONFIGURATION: 
  - db filename, defaulting to monitor.db. 
- MailHandler: sends all responses that aren't HTTP status code 200 to a list of email addresses. 
CONFIGURATION: 
  - to ['%EMAIL', '%ADDRESS', '%LIST'],
  - '%LOGIN',
  - '%PASSWORD'
  - smtp server, defaulting to 'smtp.gmail.com:587',
  - email from name, defaulting to 'Production Monitor'
- SlackHandler: posts all responses that aren't HTTP status code 200 to a slack webhook channel.
CONFIGURATION: 
  - '%SLACK_HOOK_URL',
  - '%SLACK_CHANNEL',

## Usage
The following example will make a HTTP GET request to `https://foo.com` and `https://b.foo.com/path` every 900 seconds (15 minutes)
```
python webserver_monitor.py -u https://foo.com -u https://b.foo.com/path -r 900
```

