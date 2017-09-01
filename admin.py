#!/usr/bin/env python3
import os
import argparse
import json
import datetime
from app import app, db, DiscordExport, Server, User, Channel, Message

def create_db():
    pass

def import_json(filename):
    pass

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
