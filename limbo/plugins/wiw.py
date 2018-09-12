"""
!wiw - outputs the information for what is deployed where.
!wiw set <format> <url> [api token] Set the format and URL to use for the current channel.
    <format> One of the following formats: (ecs)
    <url> Url to the what-is-where endpoint
    [api token] (optional)
"""

import argparse
import json
import re
import requests

# Available formats
FORMATS = ['ecs']


def wiw(msg, server):
    wiwEndpoint = get_wiw_endpoint(server, msg["channel"])

    if not wiwEndpoint:
        return "This channel has not yet been setup, use !wiw set.\n" + __doc__

    if wiwEndpoint['format'] == 'ecs':
        headers = {'x-api-key': wiwEndpoint['api_token']}

        res = requests.get(wiwEndpoint['url'], headers=headers)

        if res.status_code == 200:
            output = ""

            for loadBalancer, listeners in res.json().items():
                output += "{0}\n".format(loadBalancer)

                for listener, rules in listeners.items():
                    output += "\t{0}\n".format(listener)

                    for rule, apps in rules.items():
                        output += "\t\t{0}\n".format(rule)

                        for app in apps:
                            output += "\t\t\t{0}\n".format(app)

            return output

        return "Error; Got response: {0}".format(res.text)

    return "Something went wrong, try running !wiw set again."


def get_wiw_endpoint(server, room):
    rows = server.query(
        '''SELECT format, url, api_token FROM wiw_endpoints WHERE room = ? LIMIT 1''',
        room)

    if rows:
        return {
            'format': rows[0][0],
            'url': rows[0][1],
            'api_token': rows[0][2]
        }

    return None


def set_wiw_endpoint(server, room, format, url, apiToken):
    server.query('''DELETE FROM wiw_endpoints WHERE room = ?''', room)
    server.query(
        '''INSERT INTO wiw_endpoints(room, format, url, api_token)
        VALUES (?, ?, ?, ?)''', room, format, url, apiToken)


# Only run create_database on this module's first execution
FIRST = True


def create_database(server):
    server.query('''CREATE TABLE IF NOT EXISTS wiw_endpoints
            (room text, format text, url text, api_token text)''')
    FIRST = False


ARGPARSE = argparse.ArgumentParser()
ARGPARSE.add_argument('command', nargs=1)
ARGPARSE.add_argument('body', nargs='*')


def on_message(msg, server):
    if FIRST:
        create_database(server)

    text = msg.get("text", "")
    match = re.findall(r"!wiw\s*(.*)?", text)
    if not match:
        return

    # If given -h or -v, argparse will try to quit. Don't let it.
    try:
        ns = ARGPARSE.parse_args(match[0].split(' '))
    except SystemExit:
        return __doc__
    command = ns.command[0]

    # if the user calls !wiw with no arguments, print the wiw status
    if not len(command):
        return wiw(msg, server)

    if command == 'help':
        return __doc__

    if command == 'set':
        if len(ns.body) < 2:
            return "<format> and <url> are required\n" + __doc__

        format = ns.body[0]
        url = ns.body[1]
        apiToken = ''

        # API key is optional
        if len(ns.body) > 2:
            apiToken = ns.body[2]

        if format not in FORMATS:
            return "Format not supported. Choose one of: {0}".format(FORMATS)

        return set_wiw_endpoint(server, msg["channel"], format, url, apiToken)


on_bot_message = on_message
