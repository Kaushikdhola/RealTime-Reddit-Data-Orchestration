from flask import Flask, render_template, request, jsonify
import requests
import os

app = Flask(__name__)

api_url = os.environ.get('GENERATED_API_LIKE')

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        return render_template('index.html')

    elif request.method == 'POST':
        print("Sending request to Lambda")
        response = requests.post(api_url, json=request.json)
        return jsonify(response.json())

if __name__ == '__main__':
    app.run(debug=True)