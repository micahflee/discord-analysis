# Discord JSON Search

A tool to search Discord JSON files for keywords, and showing you specific messages that include those keywords, as well as the channels they're in.

## Getting started

Install dependencies:

```sh
$ virtualenv-3 env
$ . env/bin/activate
(env) $ pip3 install -r requirements.txt
```

Copy `app.cfg-sample` to `app.cfg` and edit it to specify database settings.

Initialize the database:

```sh
(env) $ ./admin.py create-db
(env) $ ./admin.py import-json [filename.json] # do this for each JSON file
```

To start the app:

```sh
(env) $ ./app.py
```

## Simple command line tool

You can also use `discord-json-search` to search an individual JSON file for keywords.
