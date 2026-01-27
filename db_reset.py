from flask import Flask
from config import SQLALCHEMY_DATABASE_URI
from models import db

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

with app.app_context():
    db.drop_all()
    db.create_all()
    print("✅ Database reset successfully (tables recreated).")
