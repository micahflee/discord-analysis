# Discord JSON Search

A tool to search Discord JSON files for keywords, and showing you specific messages that include those keywords, as well as the channels they're in.

## Getting started

Copy `config.json-sample` to `config.json`, and then edit it.

Copy `app.cfg-sample` to `app.cfg` and edit it to specify database settings.

Install dependencies:

```sh
$ virtualenv-3 env
$ . env/bin/activate
(env) $ pip3 install -r requirements.txt
```
To start the app:

```sh
(env) $ ./app.py
```
