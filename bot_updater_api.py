from flask import Flask, jsonify, request
from flask_cors import CORS, cross_origin

app = Flask(__name__)
CORS(app)

@cross_origin(origins="http://127.0.0.1:8080", supports_credentials=True)
@app.route('/login', methods=['POST', 'GET'])
def route():
    req = request.get_json()
    print(req['word'])
    return jsonify({'msg':'msg'})
@app.after_request
def add_header(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Access-Control-Allow-Headers, Origin, X-Requested-With, Content-Type, Accept, Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS, HEAD'
    response.headers['Access-Control-Expose-Headers'] = '*'
    return response

if __name__ == "__main__":
  app.run(host='0.0.0.0', port=8081, debug=True)