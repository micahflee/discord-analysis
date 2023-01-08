#!/usr/bin/python3
import sys
import argparse
import json
import datetime

def colored(msg, color=None, bold=False, underline=False):
    c = {
        'purple': '\033[95m',
        'blue': '\033[94m',
        'green': '\033[92m',
        'yellow': '\033[93m',
        'red': '\033[91m',
        'gray': '\033[90m',
        'end': '\033[0m',
        'bold': '\033[1m',
        'underline': '\033[4m'
    }
    s = ''
    if bold:
        s += c['bold']
    if underline:
        s += c['underline']
    if color:
        s += c[color]
    s += msg
    s += c['end']
    return s

def highlight(message, query):
    new_message = ''
    index = 0
    while True:
        new_index = message.lower().find(query.lower(), index)
        if new_index > 0:
            # Found
            new_message += message[index:new_index]
            new_message += colored(message[new_index:new_index+len(query)], underline=True)
            index = new_index + len(query)
        else:
            # Not found
            new_message += message[index:]
            break

    return new_message

def display(channel_name, server_name, user_name, timestamp, message, query):
    print('{} {}'.format(colored('#{}'.format(channel_name), 'purple'), colored('[server: {}]'.format(server_name), 'gray')))
    print('{} {}'.format(colored(user_name, bold=True), colored(timestamp.strftime('%c'), 'gray')))
    print(highlight(message, query))
    print('')

def search(data, query):
    # Loop through each channel
    for channel_id in data['data']:
        # Get the channel name and server name
        channel_name = data['meta']['channels'][channel_id]['name']
        server_name = data['meta']['servers'][data['meta']['channels'][channel_id]['server']]['name']

        for message_id in data['data'][channel_id]:
            # Pull the user data, timestamp, and message body from the message
            user_index = data['data'][channel_id][message_id]['u']
            user_id = data['meta']['userindex'][user_index]
            user_name = data['meta']['users'][user_id]['name']
            timestamp = datetime.datetime.fromtimestamp(data['data'][channel_id][message_id]['t'] / 1000)
            message = data['data'][channel_id][message_id]['m']

            # Is the query in the message?
            if query.lower() in message.lower():
                display(channel_name, server_name, user_name, timestamp, message, query)

def main():
    # Arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("filename", help="Discord JSON filename")
    parser.add_argument("query", help="Search query")
    parser.parse_args()
    args = parser.parse_args()

    filename = args.filename
    query = args.query

    # Load the json file
    try:
        with open(filename) as data_file:
            data = json.load(data_file)
    except:
        print('Failed to load JSON file')
        sys.exit()

    # Search
    search(data, query)

if __name__ == '__main__':
    main()
