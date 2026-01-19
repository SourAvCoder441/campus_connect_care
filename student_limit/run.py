from flask import Flask
from app.student_portal.routes import student_bp
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "app", "templates"),
    static_folder=os.path.join(BASE_DIR, "app", "styles")
)

app.secret_key = "dev-secret-key"

app.register_blueprint(student_bp, url_prefix="/student")

if __name__ == "__main__":
    app.run(debug=True)
