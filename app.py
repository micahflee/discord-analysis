#!/usr/bin/env python3
import json
import datetime

from flask import Flask, render_template, request, escape, flash, redirect
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config.from_pyfile("app.cfg")

# Hack to support mysql and unicode
use_mysql = app.config["SQLALCHEMY_DATABASE_URI"].startswith("mysql")
if use_mysql:
    from sqlalchemy.dialects.mysql import VARCHAR, TEXT

db = SQLAlchemy(app)

# Get the page and per_page args from query string, as ints
def get_pagination_args():
    page = request.args.get("page", 1)
    per_page = request.args.get("per_page", 2000)
    return (int(page), int(per_page))


# A discord server
class Server(db.Model):
    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    if use_mysql:
        name = db.Column(
            VARCHAR(128, charset="utf8mb4", collation="utf8mb4_unicode_ci"),
            unique=True,
            nullable=False,
        )
    else:
        name = db.Column(db.String(128), unique=True, nullable=False)

    channels = db.relationship("Channel", back_populates="server")
    messages = db.relationship("Message", back_populates="server")

    def __init__(self, name):
        self.name = name


# A user in a chat room team
class User(db.Model):
    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    discord_id = db.Column(db.String(128), unique=True, nullable=False)

    if use_mysql:
        name = db.Column(
            VARCHAR(128, charset="utf8mb4", collation="utf8mb4_unicode_ci")
        )
    else:
        name = db.Column(db.String(128))

    messages = db.relationship("Message", back_populates="user")

    def __init__(self, discord_id, name):
        self.discord_id = discord_id
        self.name = name

    def permalink(self):
        return "/user/{}".format(self.id)

    def message_count(self):
        return Message.query.filter_by(user=self).count()


# A channel
class Channel(db.Model):
    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    discord_id = db.Column(db.String(128), unique=True, nullable=False)
    if use_mysql:
        name = db.Column(
            VARCHAR(128, charset="utf8mb4", collation="utf8mb4_unicode_ci")
        )
    else:
        name = db.Column(db.String(128))

    messages = db.relationship("Message", back_populates="channel")

    server_id = db.Column(db.Integer, db.ForeignKey("server.id"))
    server = db.relationship("Server", back_populates="channels")

    def __init__(self, server, discord_id, name):
        self.server = server
        self.discord_id = discord_id
        self.name = name

    def permalink(self):
        return "/channel/{}".format(self.id)

    def message_count(self):
        return Message.query.filter_by(channel=self).count()


# A message posted in a channel
class Message(db.Model):
    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    discord_id = db.Column(db.String(128), unique=True, nullable=False)
    timestamp = db.Column(db.DateTime)
    if use_mysql:
        message = db.Column(
            VARCHAR(4096, charset="utf8mb4", collation="utf8mb4_unicode_ci")
        )
        attachments_json = db.Column(
            VARCHAR(4096, charset="utf8mb4", collation="utf8mb4_unicode_ci")
        )
    else:
        message = db.Column(db.String(4096))
        attachments_json = db.Column(db.String(4096))

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User", back_populates="messages")

    channel_id = db.Column(db.Integer, db.ForeignKey("channel.id"))
    channel = db.relationship("Channel", back_populates="messages")

    server_id = db.Column(db.Integer, db.ForeignKey("server.id"))
    server = db.relationship("Server", back_populates="messages")

    def __init__(
        self,
        server,
        discord_id,
        timestamp,
        message,
        user,
        channel,
        attachments_json=None,
    ):
        self.server = server
        self.discord_id = discord_id
        self.timestamp = datetime.datetime.fromtimestamp(timestamp / 1000)
        self.message = message
        self.user = user
        self.channel = channel
        if attachments_json:
            self.attachments_json = attachments_json

    def formatted_timestamp(self):
        return self.timestamp.strftime("%b %d, %Y %I:%M:%S %p")

    def permalink(self):
        return "/view/{}".format(self.id)

    def highlight(self, query):
        # Make sure to escape the message here, and replace newslines with line breaks
        m = str(escape(self.message)).replace("\n", "<br>\n")

        # If there isn't a query, return the original message
        if not query:
            return m

        new_m = ""
        index = 0
        while True:
            new_index = m.lower().find(query.lower(), index)
            if new_index > 0:
                # Found
                new_m += m[index:new_index]
                new_m += "<span class='highlight'>{}</span>".format(
                    m[new_index : new_index + len(query)]
                )
                index = new_index + len(query)
            else:
                # Not found
                new_m += m[index:]
                break

        return new_m

    def attachments(self):
        if not self.attachments_json:
            return []

        return json.loads(self.attachments_json)


data = None


@app.route("/")
def index():
    servers = Server.query.all()
    return render_template("index.html", servers=servers)


@app.route("/search")
def search():
    q = request.args.get("q")
    s = request.args.get("s", 0)
    if s == "":
        s = 0
    page, per_page = get_pagination_args()

    server = Server.query.filter_by(id=s).first()

    messages = Message.query
    if server:
        messages = messages.filter_by(server=server)
    pagination = (
        messages.filter(Message.message.like("%{}%".format(q)))
        .order_by(Message.timestamp)
        .paginate(page=page, per_page=per_page)
    )

    if server:
        description = "Search {}: {}".format(server.name, q)
    else:
        description = "Search: {}".format(q)

    servers = Server.query.all()
    pagination_link = "/search?q={}&s={}".format(q, s)
    return render_template(
        "results.html",
        q=q,
        s=int(s),
        servers=servers,
        pagination=pagination,
        pagination_link=pagination_link,
        description=description,
    )


@app.route("/view/<int:message_id>")
def view(message_id):
    q = request.args.get("q")

    # Look up the Message
    message = Message.query.filter_by(id=message_id).first()
    if not message:
        flash("Invalid message")
        return redirect("/")

    # Find messages before and after this one
    prev_messages = (
        Message.query.filter_by(channel=message.channel)
        .filter(Message.timestamp < message.timestamp)
        .order_by(Message.timestamp.desc())
        .limit(20)
        .all()
    )
    prev_messages.reverse()
    next_messages = (
        Message.query.filter_by(channel=message.channel)
        .filter(Message.timestamp > message.timestamp)
        .order_by(Message.timestamp)
        .limit(20)
        .all()
    )

    # Create a description
    description = "Message by {}, in {}, #{}".format(
        message.user.name, message.server.name, message.channel.name
    )

    servers = Server.query.all()
    return render_template(
        "view.html",
        q=q,
        s=message.server.id,
        channel=message.channel,
        servers=servers,
        description=description,
        active_message_id=message.id,
        message=message,
        prev_messages=prev_messages,
        next_messages=next_messages,
    )


@app.route("/channel/<int:channel_id>")
def channel(channel_id):
    page, per_page = get_pagination_args()

    # Look up the Channel
    channel = Channel.query.filter_by(id=channel_id).first()
    if not channel:
        flash("Invalid channel")
        return redirect("/")

    # Look up messages
    pagination = (
        Message.query.filter_by(channel=channel)
        .order_by(Message.timestamp)
        .paginate(page=page, per_page=per_page)
    )

    # Description
    description = "Messages in {}, #{}".format(channel.server.name, channel.name)

    servers = Server.query.all()
    pagination_link = "/channel/{}?".format(channel_id)
    return render_template(
        "results.html",
        s=channel.server.id,
        channel=channel,
        servers=servers,
        pagination=pagination,
        pagination_link=pagination_link,
        description=description,
    )


@app.route("/users")
def user_list():
    users = User.query.all()
    servers = Server.query.all()
    return render_template("user_list.html", servers=servers, users=users)


@app.route("/user/<int:user_id>")
def user(user_id):
    page, per_page = get_pagination_args()

    # Look up the User
    user = User.query.filter_by(id=user_id).first()
    if not user:
        flash("Invalid user")
        return redirect("/")

    # Look up messages
    pagination = (
        Message.query.filter_by(user=user)
        .order_by(Message.timestamp)
        .paginate(page=page, per_page=per_page)
    )

    # Description
    description = "Messages from @{}".format(user.name)

    servers = Server.query.all()
    pagination_link = "/user/{}?".format(user_id)
    return render_template(
        "results.html",
        servers=servers,
        pagination=pagination,
        pagination_link=pagination_link,
        description=description,
    )


def main():
    app.run()


if __name__ == "__main__":
    main()
