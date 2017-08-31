#!/usr/bin/env python3
import json
import os

from flask import Flask, render_template, url_for
app = Flask(__name__)

data = None

@app.route('/')
def index():
    return render_template('index.html', files=data['files'])

def sizeof_fmt(num, suffix='B'):
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)

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

    app.run(debug=True)

if __name__ == '__main__':
    main()
