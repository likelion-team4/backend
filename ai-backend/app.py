from flask import Flask
from routes.overview import bp as overview_bp

app = Flask(__name__)
app.register_blueprint(overview_bp)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)