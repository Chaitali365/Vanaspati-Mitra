from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class MedicinalPlant(db.Model):
    __tablename__ = "medicinal_plant"

    id = db.Column(db.Integer, primary_key=True)

    plant_name = db.Column(db.String(200), nullable=False)
   

    synonyms = db.Column(db.Text)          # ✅ NEW
    disease = db.Column(db.Text)

    # ✅ Body type wise usage
    how_to_use_vatta = db.Column(db.Text)  # ✅ NEW
    how_to_use_pitta = db.Column(db.Text)  # ✅ NEW
    how_to_use_kapha = db.Column(db.Text)  # ✅ NEW

    # (Optional) old common usage (keep it for backward support)
    how_to_use = db.Column(db.Text)

    part_used = db.Column(db.Text)         # ✅ NEW
    gunna = db.Column(db.Text)             # ✅ NEW

    image = db.Column(db.String(255))      # ✅ MUST be VARCHAR


class User(db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)


class Favorite(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    plant_id = db.Column(db.Integer, db.ForeignKey("medicinal_plant.id"), nullable=False)

    # ✅ body type saved when user clicks save
    body_type = db.Column(db.String(20), nullable=True)  # vatta / pitta / kapha

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # relation with plant
    plant = db.relationship("MedicinalPlant", backref=db.backref("favorites", lazy=True))
