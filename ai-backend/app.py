from flask import Flask
from flask_cors import CORS
from routes.overview import bp as overview_bp

app = Flask(__name__)
CORS(app)

app.register_blueprint(overview_bp)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)