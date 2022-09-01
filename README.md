# Discord JSON Search

A tool to search Discord JSON files for keywords, and showing you specific messages that include those keywords, as well as the channels they're in.

## Getting started

Install dependencies:

```sh
$ python3 -m venv venv
$ . venv/bin/activate
(env) $ pip3 install -r requirements.txt
```

Copy `app.cfg-sample` to `app.cfg` and edit it to specify database settings.

Initialize the database:

```sh
(venv) $ ./admin.py create-db
(venv) $ ./admin.py import-json [filename.json] # do this for each JSON file
```

To start the app:

```sh
(venv) $ ./app.py
```

## Simple command line tool

You can also use `discord-json-search` to search an individual JSON file for keywords.
