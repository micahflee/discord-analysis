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
        return '/view/{}/{}'.format(self.channel.id, int(self.timestamp.timestamp()))

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
    description = 'Search: {}'.format(q)
    return render_template('view.html', messages=messages, q=q, description=description)

@app.route('/view/<channel_id>/<int:ts>')
def view(channel_id, ts):
    q = request.args.get('q')

    # Look up the Channel
    channel = Channel.query.filter_by(id=channel_id).first()
    if not channel:
        flash('Invalid channel')
        return redirect('/')

    # Find all of the messages in this channel within an hour of the timestamp
    ts = datetime.datetime.fromtimestamp(ts)
    one_hour = datetime.timedelta(hours=1)

    messages = Message.query.filter(Message.timestamp > ts - one_hour).filter(Message.timestamp < ts + one_hour).order_by(Message.timestamp).all()

    # Create a description
    def format_ts(ts):
        return ts.strftime('%b %d, %Y %I:%M:%S %p')
    description = 'Messages in #{} from {} to {}'.format(channel.name, format_ts(ts-one_hour), format_ts(ts+one_hour))

    return render_template('view.html', messages=messages, q=q, description=description)

def main():
    app.run()

if __name__ == '__main__':
    main()
