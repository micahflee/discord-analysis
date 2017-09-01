#!/usr/bin/env python3
import json
import os
import datetime
import re

from flask import Flask, render_template, url_for, request, escape, flash, redirect
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config.from_pyfile('app.cfg')
db = SQLAlchemy(app)

# An exported Discord team, representing a JSON file
class DiscordExport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(128))
    basename = db.Column(db.String(128))
    size = db.Column(db.Integer)

    servers = db.relationship("Server", back_populates="discord_export")
    users = db.relationship("User", back_populates="discord_export")

    def __init__(self, filename):
        self.filename = filename
        self.basename = os.path.basename(filename)
        self.size = os.stat(filename).st_size

    def human_readable_size(self):
        num = self.size
        suffix='B'
        for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
            if abs(num) < 1024.0:
                return "%3.1f%s%s" % (num, unit, suffix)
            num /= 1024.0
        return "%.1f%s%s" % (num, 'Yi', suffix)

# A discord server
class Server(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128))

    channels = db.relationship("Channel", back_populates="server")

    discord_export_id = db.Column(db.Integer, db.ForeignKey('discord_export.id'))
    discord_export = db.relationship("DiscordExport", back_populates="servers")

    def __init__(self, name, discord_export):
        self.name = name
        self.discord_export = discord_export

# A user in a chat room team
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    discord_id = db.Column(db.String(128))
    name = db.Column(db.String(128))

    messages = db.relationship("Message", back_populates="user")

    discord_export_id = db.Column(db.Integer, db.ForeignKey('discord_export.id'))
    discord_export = db.relationship("DiscordExport", back_populates="users")

    def __init__(self, discord_id, name, discord_export):
        self.discord_id = discord_id
        self.name = name
        self.discord_export = discord_export

# A channel
class Channel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    discord_id = db.Column(db.String(128))
    name = db.Column(db.String(128))

    messages = db.relationship("Message", back_populates="channel")

    server_id = db.Column(db.Integer, db.ForeignKey('server.id'))
    server = db.relationship("Server", back_populates="channels")

    def __init__(self, discord_id, name, server):
        self.discord_id = discord_id
        self.name = name
        self.server = server

# A message posted in a channel
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    discord_id = db.Column(db.String(128))
    timestamp = db.Column(db.DateTime)
    message = db.Column(db.String(1024))
    attachments_json = db.Column(db.String(1024))

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship("User", back_populates="messages")

    channel_id = db.Column(db.Integer, db.ForeignKey('channel.id'))
    channel = db.relationship("Channel", back_populates="messages")

    def __init__(self, discord_id, timestamp, message, user, channel, attachments_json=None):
        self.discord_id = discord_id
        self.timestamp = datetime.datetime.fromtimestamp(timestamp / 1000)
        self.message = message
        self.user = user
        self.channel = channel
        if attachments_json:
            self.attachments_json = attachments_json

    def formatted_timestamp(self):
        return self.timestamp.strftime('%b %d, %Y %I:%M:%S %p')

    def permalink(self):
        return '/view/{}/{}/{}'.format(self.channel.server.discord_export.basename, self.channel.name, self.timestamp.timestamp())

    def highlight(self, query):
        # Make sure to escape the message here, and replace newslines with line breaks
        m = str(escape(self.message)).replace('\n', '<br>\n')

        # If there isn't a query, return the original message
        if not query:
            return m

        new_m = ''
        index = 0
        while True:
            new_index = m.lower().find(query.lower(), index)
            if new_index > 0:
                # Found
                new_m += m[index:new_index]
                new_m += "<span class='highlight'>{}</span>".format(m[new_index:new_index+len(query)])
                index = new_index + len(query)
            else:
                # Not found
                new_m += m[index:]
                break

        return new_m

    def attachments(self):
        if not self.attachments_json:
            return []

        return json.loads(self.attachments_json.replace("'", '"'))

data = None

@app.route('/')
def index():
    data_exports = DiscordExport.query.all()
    return render_template('index.html', data_exports=data_exports)

@app.route('/search')
def search():
    q = request.args.get('q')
    messages = Message.query.filter(Message.message.like("%{}%".format(q))).order_by(Message.timestamp).all()
    return render_template('search.html', messages=messages, q=q)

"""
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
"""

def main():
    app.run()

if __name__ == '__main__':
    main()
