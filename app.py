#!/usr/bin/env python3
import json
import os
import datetime

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
                # Pull the user data, timestamp, and message body from the message
                user_index = json_data['data'][channel_id][message_id]['u']
                user_id = json_data['meta']['userindex'][user_index]
                user_name = json_data['meta']['users'][user_id]['name']
                formatted_ts = ts_fmt(json_data['data'][channel_id][message_id]['t'])
                message = json_data['data'][channel_id][message_id]['m']

                # Is the query in the message?
                if q.lower() in message.lower():
                    messages.append({
                        'basename': basename,
                        'channel_name': channel_name,
                        'server_name': server_name,
                        'user_name': user_name,
                        'ts': json_data['data'][channel_id][message_id]['t'],
                        'formatted_ts': formatted_ts,
                        'safe_message': highlight(message, q)
                    })

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
        message_ts = channel_data[message_id]['t']
        if range_from < message_ts < range_to:
            m = channel_data[message_id]
            user_id = json_data['meta']['userindex'][m['u']]
            user_name = json_data['meta']['users'][user_id]['name']
            formatted_ts = ts_fmt(json_data['data'][channel_id][message_id]['t'])

            messages.append({
                'basename': basename,
                'channel_name': channel_name,
                'server_name': server_name,
                'user_name': user_name,
                'ts': m['t'],
                'formatted_ts': formatted_ts,
                'safe_message': highlight(m['m'], q)
            })

    # Now sort messages by timestamp
    messages.sort(key=lambda x: x['ts'])

    # Create a description
    description = 'Messages in #{} from {} to {}'.format(channel_name, ts_fmt(range_from), ts_fmt(range_to))

    return render_template('view.html', messages=messages, q=q, description=description)

def highlight(message, query):
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
