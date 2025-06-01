from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/data')
def send_data():
    return jsonify({"message": "Привіт із Python!"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)