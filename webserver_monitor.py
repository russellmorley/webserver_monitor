import sys, getopt
import urllib.request
import time
import datetime
import sqlite3
import os.path
from threading import Event, Thread
import smtplib
import json

class Handler(object):
    def open(self):
        pass

    def handle_code(self, url, code):
        if code!=200:
            print("{} ERROR: GET {} returned {}".format(datetime.datetime.utcnow().isoformat(), url, code))
        else:
            print("{} Active: GET {} returned {}".format(datetime.datetime.utcnow().isoformat(), url, code))
        
    def handle_exception(self, url, ex):
        print("{} ERROR GET {}: {}".format(datetime.datetime.utcnow().isoformat(), url, ex))

    def close(self):
        pass

class DBHandler(Handler):

    def __init__(self, file_name):
        self.file_name = file_name if file_name is not None else "default.db"

    def open(self):
        self.conn = sqlite3.connect(self.file_name)
        self.cursor = self.conn.cursor()
        #create table if it doesn't already exist
        try:
            self.cursor.execute('''CREATE TABLE status (date text, url text, info text)''')
            self.conn.commit()
        except sqlite3.OperationalError:
            pass

    def handle_code(self, url, code):
        self.cursor.execute("INSERT INTO status VALUES ('{}','{}','{}')".format(datetime.datetime.utcnow().isoformat(), url, code))
        self.conn.commit()

    def handle_exception(self, url, ex):
        self.cursor.execute("INSERT INTO status VALUES ('{}','{}','{}')".format(datetime.datetime.utcnow().isoformat(), url, str(ex)))
        self.conn.commit()

    def close(self):
        self.conn.close()

class MailHandler(Handler):

    def __init__(self, smtp_server, from_address, to_address_list, login, password):
        self.smtp_server = smtp_server
        self.from_address = from_address
        self.to_address_list = to_address_list
        self.login = login
        self.password = password

    def open(self):
        pass

    def handle_code(self, url, code):
        if code != 200:
            self.send(
                'TROUBLE ACCESSING {}'.format(url),
                'GET returned {}'.format(code),
            )

    def handle_exception(self, url, ex):
        self.send(
            "TROUBLE ACCESSING {}".format(url),
            str(ex)
        )

    def close(self):
        pass

    def send(
        self,
        subject,
        message,
    ):
        header  = 'From: {}\n'.format(self.from_address)
        header += 'To: {}\n'.format(','.join(self.to_address_list))
        header += 'Subject: {}\n\n'.format(subject)
        message = header + message
        server = smtplib.SMTP(self.smtp_server)
        server.starttls()
        server.login(self.login, self.password)
        problems = server.sendmail(self.from_address, self.to_address_list, message)
        server.quit()

class SlackHandler(Handler):

    def __init__(self, server, channel):
        self.server = server
        self.channel = channel

    def open(self):
        pass

    def handle_code(self, url, code):
        if code != 200:
            self.send(
                'TROUBLE ACCESSING {}. GET returned {}'.format(url, code)
            )

    def handle_exception(self, url, ex):
        self.send(
            "TROUBLE ACCESSING {}: {}".format(url, str(ex))
        )

    def close(self):
        pass

    def send(self, message):
        data={
            "payload": json.dumps({
                "channel": self.channel,
                "text": message
            })
        }
        req = urllib.request.Request(self.server)
        data = urllib.parse.urlencode(data)
        req.add_header("Content-type", "application/x-www-form-urlencoded; charset=text/plain")
        databytes = data.encode('utf-8')   # needs to be bytes
        req.add_header('Content-Length', len(databytes))
        response = urllib.request.urlopen(req, databytes)

class Monitor(object):

    def start(self, url, verbose, repeat_secs, *handlers):
        self.url = url
        self.verbose = verbose
        self.repeat_secs = repeat_secs
        self.handlers = handlers
        self.stop_running = False
        self.event = Event()
        self.thread = Thread(target = self.run)
        self.thread.start()

    def get_thread(self):
        return self.thread

    def run(self):
        #open handlers
        for handler in self.handlers:
            handler.open()

        #run loop
        while(not self.stop_running):
            try:
                code = Monitor.get_request_returncode(self.url)
                for handler in self.handlers:
                    handler.handle_code(self.url, code)
            except Exception as ex:
                for handler in self.handlers:
                    handler.handle_exception(self.url, ex)
            self.event.wait(timeout=self.repeat_secs)

        #close handlers
        for handler in self.handlers:
            handler.close()

    def stop(self):
        self.stop_running = True
        self.event.set()
        self.thread.join()

    @staticmethod
    def get_request_returncode(url):
        conn = urllib.request.urlopen(url)
        return conn.getcode()


def main():
    usage = "USAGE: {} -u URL [-u URL...] -r repeat_secs"
    name = sys.argv[0]
    output = None
    verbose = False
    urls = []
    repeat_secs = None
    file_name = None
    monitors = []

    try:
        opts, hander_name_list = getopt.getopt(sys.argv[1:], "hu:r:v", ["help", "url", "repeat",])
    except getopt.GetoptError as err:
        # print help information and exit:
        print(err)
        print(usage.format(name))
        sys.exit(2)
    #if len(opts) < 1 or len(hander_name_list) < 1:
    #    print(usage.format(name))
    #    sys.exit()
    for k, v in opts:
        if k in ("-h", "--help"):
            print(usage.format(name))
            sys.exit()
        elif k == "-v": 
            verbose = True
        elif k in ("-u", "--url"):
            urls.append(v)
        elif k in ("-r", "--repeat"):
            repeat_secs = int(v)
        else:
            assert False, "unhandled option"
    if len(urls) < 1 or repeat_secs == None:
        print(usage.format(name))
        sys.exit()
    else:
        for url in urls:
            monitor = Monitor()
            monitor.start(
                url,
                verbose,
                repeat_secs,
                Handler(),
                DBHandler("monitor.db"),
                MailHandler(
                    'smtp.gmail.com:587',
                    'Production Monitor',
                    ['%EMAIL', '%ADDRESS', '%LIST'],
                    '%LOGIN',
                    '%PASSWORD'
                ),
                SlackHandler(
                    '%SLACK_HOOK_URL',
                    '%SLACK_CHANNEL',
                )
            )
            monitors.append(monitor)
        var = input("Press enter to stop\n\n")
        print("Exiting...")
        for monitor in monitors:
            monitor.stop()
        print("exited.")

if __name__ == "__main__":
    main()


