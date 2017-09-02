#!/usr/bin/env python3
import os
import argparse
import json
import datetime
from app import app, db, DiscordExport, Server, User, Channel, Message

def create_db():
    db_path = app.config['SQLALCHEMY_DATABASE_URI'][10:] # strip "sqlite://"
    if os.path.isfile(db_path):
        print("Database already exists")
    else:
        db.create_all()

def import_json(filename):
    # Import JSON file
    with open(filename) as f:
        data = json.load(f)

    # Add the DiscordExport
    discord_export = DiscordExport(filename)
    db.session.add(discord_export)
    db.session.commit()

    # Add the users
    count = 0
    for user_discord_id in data['meta']['users']:
        name = data['meta']['users'][user_discord_id]['name']

        user = User(user_discord_id, name, discord_export)
        db.session.add(user)

        count += 1
    db.session.commit()
    print("Added {} users".format(count))

    # Add the servers
    count = 0
    for item in data['meta']['servers']:
        name = item['name']

        server = Server(name, discord_export)
        db.session.add(server)

        count += 1
    db.session.commit()
    print("Added {} servers".format(count))

    # Add the channels
    count = 0
    for channel_discord_id in data['meta']['channels']:
        name = data['meta']['channels'][channel_discord_id]['name']
        server_id = data['meta']['channels'][channel_discord_id]['server']
        server = Server.query.filter_by(name=data['meta']['servers'][server_id]['name']).first()

        channel = Channel(channel_discord_id, name, server)
        db.session.add(channel)

        count += 1
    db.session.commit()
    print("Added {} channels".format(count))

    # Loop through each channel
    count = 0
    for discord_channel_id in data['data']:
        # Get the channel
        channel = Channel.query.filter_by(discord_id=channel_discord_id).first()

        # Loop through each message in this channel
        for discord_message_id in data['data'][discord_channel_id]:
            timestamp = data['data'][discord_channel_id][discord_message_id]['t']
            message = data['data'][discord_channel_id][discord_message_id]['m']

            # In the de-duped json files, message['u'] points to the user_id itself, not the index
            #user_index = data['data'][discord_channel_id][discord_message_id]['u']
            #discord_user_id = data['meta']['userindex'][user_index]
            discord_user_id = data['data'][discord_channel_id][discord_message_id]['u']

            user = User.query.filter_by(discord_id=discord_user_id).first()

            if 'a' in data['data'][discord_channel_id][discord_message_id]:
                attachments_json = json.dumps(data['data'][discord_channel_id][discord_message_id]['a'])
            else:
                attachments_json = None

            message = Message(discord_message_id, timestamp, message, user, channel, discord_export, attachments_json)
            db.session.add(message)

            count += 1
    db.session.commit()
    print("Added {} messages".format(count))

if __name__ == '__main__':
    # Parse arguments
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='subcommand')
    subparsers.add_parser('create-db')
    parser_import_json = subparsers.add_parser('import-json')
    parser_import_json.add_argument('filename')
    args = parser.parse_args()

    cmd = args.subcommand

    if cmd == 'create-db':
        create_db()

    elif cmd == 'import-json':
        import_json(args.filename)

    else:
        parser.print_help()
