#!/usr/bin/env python3
import json
import os
import datetime
import re

from flask import Flask, render_template, url_for, request, escape, flash, redirect
app = Flask(__name__)

data = None

@app.route('/')
def index():
    return render_template('index.html', files=data['files'])

@app.route('/search')
def search():
    q = request.args.get('q')

    # The result data is organized by json file
    results = []

    # Loop through each file
    for file in data['files']:
        messages = []

        basename = file['basename']
        json_data = file['data']

        # Loop through each channel
        for channel_id in json_data['data']:
            # Get the channel name and server name
            channel_name = json_data['meta']['channels'][channel_id]['name']
            server_name = json_data['meta']['servers'][json_data['meta']['channels'][channel_id]['server']]['name']

            for message_id in json_data['data'][channel_id]:
                m = json_data['data'][channel_id][message_id]
                message_obj = create_message_obj(m, basename, channel_name, server_name, json_data, q)

                # Is the query in the message?
                if q.lower() in message_obj['orig_message'].lower():
                    messages.append(message_obj)

        if len(messages) > 0:
            results.append({
                'basename': basename,
                'messages': messages
            })

    return render_template('search.html', files=data['files'], results=results, q=q)

@app.route('/view/<basename>/<channel_name>/<int:ts>')
def view(basename, channel_name, ts):
    q = request.args.get('q')

    # Get the proper json_data for basename
    json_data = None
    for file in data['files']:
        if file['basename'] == basename:
            json_data = file['data']
            break

    if not json_data:
        flash('Invalid JSON file')
        return redirect('/')

    # Find the right channel
    channel_data = None
    server_name = None
    for channel_id in json_data['data']:
        if json_data['meta']['channels'][channel_id]['name'] == channel_name:
            channel_data = json_data['data'][channel_id]
            server_name = json_data['meta']['servers'][json_data['meta']['channels'][channel_id]['server']]['name']
            break

    if not channel_data:
        flash('Invalid channel')
        return redirect('/')

    # Find all of the messages within an hour of the timestamp
    one_hour = 3600000
    range_from = ts - one_hour
    range_to = ts + one_hour

    messages = []
    for message_id in channel_data:
        m = channel_data[message_id]
        message_obj = create_message_obj(m, basename, channel_name, server_name, json_data, q)

        if range_from < message_obj['ts'] < range_to:
            messages.append(message_obj)

    # Now sort messages by timestamp
    messages.sort(key=lambda x: x['ts'])

    # Create a description
    description = 'Messages in #{} from {} to {}'.format(channel_name, ts_fmt(range_from), ts_fmt(range_to))

    return render_template('view.html', messages=messages, q=q, description=description)

def create_message_obj(m, basename, channel_name, server_name, json_data, q=None):
    # Pull the user data, timestamp, and message body from the message
    user_index = m['u']
    user_id = json_data['meta']['userindex'][user_index]
    user_name = json_data['meta']['users'][user_id]['name']

    # Attachments
    if 'a' in m:
        attachments = m['a']
    else:
        attachments = None

    return {
        'basename': basename,
        'channel_name': channel_name,
        'server_name': server_name,
        'user_name': user_name,
        'ts': m['t'],
        'formatted_ts': ts_fmt(m['t']),
        'orig_message': m['m'],
        'safe_message': highlight(convert_mentions(m['m'], json_data), q),
        'attachments': attachments
    }

def convert_mentions(message, json_data):
    # TODO: fix this, doesn't totally work yet
    while True:
        match = re.search('<@\d{18}>', message)
        if not match:
            return message

        # What is the user id that was mentioned?
        match_str = match.group()
        user_id = match_str.lstrip('<@').rstrip('>')
        if user_id in json_data['meta']['users']:
            user_name = json_data['meta']['users'][user_id]['name']
            message = message.replace(match_str, user_name)
        else:
            # If the user id doesn't appear to be valid, just return the message without
            # replacing anything -- so we don't get stuck in an infinite loop
            return message

def highlight(message, query):
    if not query:
        return message

    # Make sure to escape the message here
    message = str(escape(message)).replace('\n', '<br>\n')

    new_message = ''
    index = 0
    while True:
        new_index = message.lower().find(query.lower(), index)
        if new_index > 0:
            # Found
            new_message += message[index:new_index]
            new_message += "<span class='highlight'>{}</span>".format(message[new_index:new_index+len(query)])
            index = new_index + len(query)
        else:
            # Not found
            new_message += message[index:]
            break

    return new_message

def sizeof_fmt(num, suffix='B'):
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)

def ts_fmt(discord_ts):
    return datetime.datetime.fromtimestamp(discord_ts / 1000).strftime('%b %d, %Y %I:%M:%S %p')

def main():
    global data
    data = {}

    # Load the config file
    with open('config.json') as f:
        data['config'] = json.load(f)

    # Prepare all the data
    data['files'] = []
    for filename in data['config']['filenames']:
        print("[] Parsing {}".format(filename))
        with open(filename) as f:
            json_data = json.load(f)

        data['files'].append({
            'filename': filename,
            'basename': os.path.basename(filename),
            'size': sizeof_fmt(os.stat(filename).st_size),
            'data': json_data
        })

    app.run()

if __name__ == '__main__':
    main()
