import os
import pandas as pd
from flask import Flask

from config import SQLALCHEMY_DATABASE_URI
from models import db, MedicinalPlant, Favorite

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

CSV_PATH = "data/ms.csv"
STATIC_IMAGE_FOLDER = "static/plant_images"
DEFAULT_IMAGE = "plant_images/default.jpg"


# --------------------------
# HELPERS
# --------------------------
def clean_text(x):
    if pd.isna(x) or x is None:
        return ""
    return str(x).strip()


def normalize_col(col):
    """Make column name lowercase + remove spaces/underscores"""
    return str(col).strip().lower().replace(" ", "_")


def get_value(row, *possible_cols):
    """
    Find value from row using multiple possible column names
    """
    for col in possible_cols:
        if col in row and pd.notna(row[col]):
            return clean_text(row[col])
    return ""


def normalize_image(value):
    if not value:
        return DEFAULT_IMAGE

    value = str(value).replace("\\", "/").strip()
    filename_csv = value.split("/")[-1].lower()

    if os.path.exists(STATIC_IMAGE_FOLDER):
        for real_file in os.listdir(STATIC_IMAGE_FOLDER):
            if real_file.lower() == filename_csv:
                return f"plant_images/{real_file}"

    return DEFAULT_IMAGE


# --------------------------
# MAIN IMPORT
# --------------------------
def import_csv_to_db():
    df = pd.read_csv(CSV_PATH)

    # normalize column headers
    df.columns = [normalize_col(c) for c in df.columns]

    with app.app_context():

        # delete favorites first (FK safe)
        Favorite.query.delete()
        db.session.commit()

        MedicinalPlant.query.delete()
        db.session.commit()

        for _, row in df.iterrows():
            row = row.to_dict()

            plant_name = get_value(row,
                "plant_name", "name", "common_name", "commonname"
            )

            synonyms = get_value(row,
                "synonyms", "synonym"
            )

            disease = get_value(row,
                "disease", "diseases"
            )

            how_vatta = get_value(row,
                "how_to_use_vatta", "how_to_use_by_vatta", "vatta", "how_to_use_for_vatta"
            )

            how_pitta = get_value(row,
                "how_to_use_pitta", "how_to_use_by_pitta", "pitta", "how_to_use_for_pitta"
            )

            how_kapha = get_value(row,
                "how_to_use_kapha", "how_to_use_by_kapha", "kapha", "how_to_use_for_kapha"
            )

            part_used = get_value(row,
                "part_used", "part_used_", "partused", "part_useds", "part_useds_", "part_used(s)", "part_used(s)_",
                "part_used", "part_used", "part_used", "part_used",
                "part_used", "part_used",
                "part_used", "part_used",
                "part_used", "part_used",
                "part_used", "part_used",
                "part_used", "part_used",
                "part_used", "part_used",
                "part_used", "part_used",
                "part_used", "part_used",
                "part_used", "part_used",
                "part_used", "part_used",
                "part_used", "part_used",
                "part_used", "part_used",
                "part_used", "part_used",
                "part_used", "part_used",
                "part_used", "part_used",
                "part_used", "part_used",
                "part_used", "part used"
            )

            gunna = get_value(row,
                "gunna", "guna", "gunas"
            )

            image_raw = get_value(row,
                "image", "image_file", "image_path"
            )

            plant = MedicinalPlant(
                plant_name=plant_name,
                synonyms=synonyms,
                disease=disease,
                how_to_use_vatta=how_vatta,
                how_to_use_pitta=how_pitta,
                how_to_use_kapha=how_kapha,
                part_used=part_used,
                gunna=gunna,
                image=normalize_image(image_raw)
            )

            db.session.add(plant)

        db.session.commit()
        print("✅ CSV Imported Successfully with correct mapping!")


if __name__ == "__main__":
    import_csv_to_db()
