#!/usr/bin/env python3
import os
import argparse
import json
import glob
import sqlalchemy
from app import app, db, Server, User, Channel, Message


def create_db():
    db_path = app.config["SQLALCHEMY_DATABASE_URI"][10:]  # strip "sqlite://"
    if os.path.isfile(db_path):
        print("Database already exists")
    else:
        with app.app_context():
            db.create_all()


def import_json(filename):
    print("Importing: {}".format(filename))

    # Import JSON file
    with open(filename) as f:
        data = json.load(f)

    with app.app_context():
        # Add the servers
        print("Adding servers: ", end="", flush=True)
        for item in data["meta"]["servers"]:
            name = item["name"]

            try:
                server = Server(name)
                db.session.add(server)
                db.session.commit()
                print("+", end="", flush=True)
            except sqlalchemy.exc.IntegrityError:
                db.session.rollback()
                print(".", end="", flush=True)
        print("")

        # Add the users
        print("Adding users: ", end="", flush=True)
        for user_discord_id in data["meta"]["users"]:
            name = data["meta"]["users"][user_discord_id]["name"]

            try:
                user = User(user_discord_id, name)
                db.session.add(user)
                db.session.commit()
                print("+", end="", flush=True)
            except sqlalchemy.exc.IntegrityError:
                db.session.rollback()
                print(".", end="", flush=True)
        print("")

        # Add the channels
        print("Adding channels: ", end="", flush=True)
        for channel_discord_id in data["meta"]["channels"]:
            name = data["meta"]["channels"][channel_discord_id]["name"]
            server_id = data["meta"]["channels"][channel_discord_id]["server"]
            server = Server.query.filter_by(
                name=data["meta"]["servers"][server_id]["name"]
            ).first()

            try:
                channel = Channel(server, channel_discord_id, name)
                db.session.add(channel)
                db.session.commit()
                print("+", end="", flush=True)
            except sqlalchemy.exc.IntegrityError:
                db.session.rollback()
                print(".", end="", flush=True)
        print("")

        # Loop through each channel in data
        for channel_discord_id in data["data"]:
            # Get the channel
            channel = Channel.query.filter_by(discord_id=channel_discord_id).first()

            # Loop through each message in this channel
            print(
                "Adding messages from {}, #{}: ".format(
                    channel.server.name, channel.name
                ), end=""
            )
            for message_discord_id in data["data"][channel_discord_id]:
                try:
                    timestamp = data["data"][channel_discord_id][message_discord_id][
                        "t"
                    ]
                    message = data["data"][channel_discord_id][message_discord_id]["m"]

                    user_index = data["data"][channel_discord_id][message_discord_id][
                        "u"
                    ]
                    user_discord_id = data["meta"]["userindex"][user_index]

                    user = User.query.filter_by(discord_id=user_discord_id).first()

                    if "a" in data["data"][channel_discord_id][message_discord_id]:
                        attachments_json = json.dumps(
                            data["data"][channel_discord_id][message_discord_id]["a"]
                        )
                    else:
                        attachments_json = None

                    message = Message(
                        channel.server,
                        message_discord_id,
                        timestamp,
                        message,
                        user,
                        channel,
                        attachments_json,
                    )
                    db.session.add(message)
                    db.session.commit()
                    print("+", end="", flush=True)
                except sqlalchemy.exc.IntegrityError:
                    db.session.rollback()
                    print(".", end="", flush=True)
            print("")

    print("Import complete")
    print("")


def user_stats():
    users = User.query.order_by(User.name).all()
    servers = Server.query.order_by(Server.name).all()

    server_users = {}

    for user in users:
        print("User: {}".format(user.name))
        for server in servers:
            message_count = (
                Message.query.filter_by(server=server).filter_by(user=user).count()
            )
            if message_count > 0:
                if server.name in server_users:
                    server_users[server.name] += 1
                else:
                    server_users[server.name] = 1

                print("- {} messages on server {}".format(message_count, server.name))
        print("")

    print("Users per server:")
    print("")
    for server_name in server_users:
        print("{}: {} users".format(server_name, server_users[server_name]))


if __name__ == "__main__":
    # Parse arguments
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="subcommand")
    subparsers.add_parser("create-db")
    parser_import_json = subparsers.add_parser("import-json")
    parser_import_json.add_argument("filename")
    subparsers.add_parser("user-stats")
    args = parser.parse_args()

    cmd = args.subcommand

    if cmd == "create-db":
        create_db()

    elif cmd == "import-json":
        filenames = glob.glob(args.filename.replace("~", os.environ["HOME"]))
        for filename in filenames:
            import_json(filename)

    elif cmd == "user-stats":
        user_stats()

    else:
        parser.print_help()
