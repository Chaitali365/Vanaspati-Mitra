from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

from config import SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS, SECRET_KEY
from models import db, MedicinalPlant, User, Favorite
from disease_aliases import normalize_disease
from plant_module.routes import plant_bp
from prakriti import prakriti_bp
from queue import Queue
from VanspatiPanchykarma.routes import vanspati_bp
#from chatbot import chatbot_bp


import pandas as pd
import os

import pyttsx3
import threading


app = Flask(__name__)
app.secret_key = SECRET_KEY

# Register Plant Module
app.register_blueprint(plant_bp)
app.register_blueprint(prakriti_bp)
app.register_blueprint(vanspati_bp, url_prefix="/vanspati")



app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = SQLALCHEMY_TRACK_MODIFICATIONS

db.init_app(app)


# ---------- LOGIN REQUIRED DECORATOR ----------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


# ---------- HOME PAGE ----------
@app.route("/")
def home():
    return render_template("home.html")




# ---------- SEARCH PAGE (PROTECTED) ----------

# ----------------------------
# GUNNA MEANINGS
# ----------------------------
ENGLISH_TO_GUNA = {
    "light": "laghu",
    "heavy": "guru",
    "dry": "ruksha",
    "oily": "snigdha",
    "sharp": "tikshna",
    "slow": "manda",
    "cold": "sheeta",
    "hot": "ushna",
    "slimy": "sara",
    "soft": "sthira"
}

GUNA_MEANINGS = {
    "laghu": "Light on the body, easy to digest",
    "guru": "Heavy, gives strength but digests slowly",
    "snigdha": "Oily, reduces dryness and nourishes",
    "ruksha": "Dry, reduces excess oil and moisture",
    "tikshna": "Strong and fast acting",
    "manda": "Slow and gentle in action",
    "sheeta": "Cooling, reduces heat and burning",
    "ushna": "Heating, improves digestion and circulation",
    "sara": "Helps movement, clears digestion and bowels",
    "sthira": "Stabilizing, calming and strengthening"
}


def format_gunna(gunna_text):
    """
    Converts: "Light, Dry"
    Into: ["Light: Light on the body, easy to digest", "Dry: Dry, reduces excess oil and moisture"]
    """
    if not gunna_text:
        return []

    result = []
    gunna_list = [g.strip().lower() for g in str(gunna_text).split(",") if g.strip()]

    for g in gunna_list:
        sanskrit_key = ENGLISH_TO_GUNA.get(g)
        if sanskrit_key:
            meaning = GUNA_MEANINGS.get(sanskrit_key, "")
            result.append(f"{g.capitalize()}: {meaning}")
        else:
            result.append(g.capitalize())

    return result

# ----------------------------
# MAIN SEARCH PAGE (INDEX.HTML)
# ----------------------------
@app.route("/search", methods=["GET", "POST"])

def search():
    results = None
    disease_value = ""
    body_value = ""

    if request.method == "POST":
        disease_value = request.form.get("disease", "").strip()
        body_value = request.form.get("body_type", "").strip().lower()

        normalized = normalize_disease(disease_value)

        plants = MedicinalPlant.query.filter(
            MedicinalPlant.disease.ilike(f"%{normalized}%")
        ).all()

        filtered_results = []

        for plant in plants:
            # attach gunna meaning list
            plant.gunna_display = format_gunna(plant.gunna)

            if body_value == "vatta" and plant.how_to_use_vatta:
                filtered_results.append(plant)

            elif body_value == "pitta" and plant.how_to_use_pitta:
                filtered_results.append(plant)

            elif body_value == "kapha" and plant.how_to_use_kapha:
                filtered_results.append(plant)

        results = filtered_results

    return render_template(
        "index.html",
        results=results,
        disease_value=disease_value,
        body_value=body_value
    )


# ---------- PLANT DETAIL ----------
@app.route("/plant/<int:id>")
@login_required
def plant_detail(id):
    plant = MedicinalPlant.query.get_or_404(id)
    return render_template("plant_detail.html", plant=plant)


# ---------- REGISTER ----------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        user = User(
            username=request.form["username"],
            password=generate_password_hash(request.form["password"])
        )
        db.session.add(user)
        db.session.commit()
        return redirect(url_for("login"))

    return render_template("register.html")


# ---------- LOGIN ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form["username"]).first()

        if user and check_password_hash(user.password, request.form["password"]):
            session["user"] = user.username

            next_page = request.args.get("next")
            return redirect(next_page or url_for("search"))

    return render_template("login.html")
# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))


# ---------- ADD TO FAVORITES ----------

@app.route("/favorite/<int:plant_id>")

def favorite(plant_id):
    # ✅ get logged in username from session
    user = User.query.filter_by(username=session["user"]).first()

    # ✅ get body_type from URL like ?body_type=vatta
    body_type = request.args.get("body_type")  # vatta/pitta/kapha

    # ✅ check already saved
    existing = Favorite.query.filter_by(
        user=user.id,
        plant_id=plant_id
    ).first()

    if not existing:
        fav = Favorite(
            user=user.id,
            plant_id=plant_id,
            body_type=body_type
        )
        db.session.add(fav)
        db.session.commit()

    return redirect(url_for("search"))


# ---------- FAVORITES ----------
@app.route("/favorites")

def favorites():
    user = User.query.filter_by(username=session["user"]).first()

    # ✅ get plant + body_type together
    data = db.session.query(MedicinalPlant, Favorite.body_type).join(
        Favorite, MedicinalPlant.id == Favorite.plant_id
    ).filter(Favorite.user == user.id).all()

    # ✅ prepare list for template
    plants = []
    for plant, body_type in data:
        plant.body_type = body_type  # attach body_type to plant object

        # ✅ gunna display list
        if plant.gunna:
            plant.gunna_display = [g.strip() for g in plant.gunna.split(",") if g.strip()]
        else:
            plant.gunna_display = []

        plants.append(plant)

    return render_template("favorites.html", plants=plants)

# -------------"seasons"--------------------------------
@app.route("/seasons", methods=["GET", "POST"])
def seasons():
    csv_path = os.path.join("data", "Medicinal Plants and Their Uses - Medicinal Plants and Their Uses.csv")
    df = pd.read_csv(csv_path)

    seasons = sorted(df["season"].dropna().unique())
    plants = []
    selected_season = None

    if request.method == "POST":
        selected_season = request.form.get("season")
        plants = df[df["season"] == selected_season].to_dict(orient="records")

    return render_template(
        "seasons.html",
        seasons=seasons,
        plants=plants,
        selected_season=selected_season
    )

# ---------- ABOUT (SEARCH + COMPARE) ----------
@app.route("/about", methods=["GET", "POST"])
def about():
    csv_path = os.path.join("data", "Medicinal Plants and Their Uses - Medicinal Plants and Their Uses.csv")
    df = pd.read_csv(csv_path)

    plant = None
    plant1 = None
    plant2 = None
    query = ""

    plant_names = sorted(df["plant_name"].dropna().unique())

    # EXISTING SINGLE SEARCH (UNCHANGED)
    if request.method == "POST" and "plant_name" in request.form:
        query = request.form.get("plant_name", "").strip().lower()
        result = df[df["plant_name"].str.lower() == query]
        if not result.empty:
            plant = result.iloc[0].to_dict()

    # NEW COMPARE FEATURE (SEPARATE & SAFE)
    if request.method == "POST" and "compare" in request.form:
        p1 = request.form.get("plant1")
        p2 = request.form.get("plant2")

        if p1 and p2:
            plant1 = df[df["plant_name"] == p1].iloc[0].to_dict()
            plant2 = df[df["plant_name"] == p2].iloc[0].to_dict()

    return render_template(
        "about.html",
        plant=plant,
        plant1=plant1,
        plant2=plant2,
        plant_names=plant_names,
        query=query
    )
# # chatbot

# ==========================================
# 1. FILE CONFIGURATION
# ==========================================
HERB_INFO_CSV = "data/Ayurvedic Medicines.csv"
REMEDY_CSV = "data/Medicinal Plants and Their Uses - Medicinal Plants and Their Uses.csv"


# Global Databases (Will hold merged data)
HERB_DETAILS_DB = []
MEDICAL_DB = {}

# ==========================================
# 2. MASSIVE HERB REACTION DB (150+ Herbs)
# ==========================================
HERB_REACTION_DB = {
    # --- A ---
    "acacia": {"energy": "Cooling", "good_for": ["Pitta", "Kapha"], "bad_for": ["Vata"], "tip": "Good for bleeding gums."},
    "aconite": {"energy": "Hot", "good_for": ["Kapha", "Vata"], "bad_for": ["Pitta"], "tip": "Toxic; use purified only."},
    "ajwain": {"energy": "Hot", "good_for": ["Vata", "Kapha"], "bad_for": ["Pitta"], "tip": "Instant gas relief."},
    "aloe vera": {"energy": "Cold", "good_for": ["Pitta"], "bad_for": ["Vata", "Kapha"], "tip": "Cooling but causes stiffness in Vata."},
    "almond": {"energy": "Warm", "good_for": ["Vata", "Pitta"], "bad_for": ["Kapha"], "tip": "Soak overnight for Pitta."},
    "amla": {"energy": "Cooling", "good_for": ["Pitta", "Vata"], "bad_for": ["Kapha"], "tip": "Best Vitamin C source."},
    "anise": {"energy": "Warm", "good_for": ["Vata", "Kapha"], "bad_for": ["Pitta"], "tip": "Digestive aid."},
    "arjuna": {"energy": "Cooling", "good_for": ["Pitta", "Kapha"], "bad_for": ["Vata"], "tip": "Heart tonic."},
    "asafoetida": {"energy": "Hot", "good_for": ["Vata", "Kapha"], "bad_for": ["Pitta"], "tip": "Prevents bloating."},
    "ashoka": {"energy": "Cold", "good_for": ["Pitta", "Kapha"], "bad_for": ["Vata"], "tip": "Uterine tonic."},
    "ashwagandha": {"energy": "Warm", "good_for": ["Vata"], "bad_for": ["Kapha"], "tip": "Strength builder; heavy to digest."},
    "asparagus": {"energy": "Cold", "good_for": ["Pitta", "Vata"], "bad_for": ["Kapha"], "tip": "Nutritive."},
    
    # --- B ---
    "bael": {"energy": "Heating", "good_for": ["Vata", "Kapha"], "bad_for": [], "tip": "Binds stool in dysentery."},
    "bala": {"energy": "Cold", "good_for": ["Vata", "Pitta"], "bad_for": ["Kapha"], "tip": "Nerve strength."},
    "bamboo": {"energy": "Cold", "good_for": ["Pitta", "Kapha"], "bad_for": ["Vata"], "tip": "High silica content."},
    "banyan": {"energy": "Cold", "good_for": ["Pitta", "Kapha"], "bad_for": ["Vata"], "tip": "Astringent for wounds."},
    "barley": {"energy": "Cold", "good_for": ["Pitta", "Kapha"], "bad_for": ["Vata"], "tip": "Diuretic and drying."},
    "basil": {"energy": "Hot", "good_for": ["Vata", "Kapha"], "bad_for": ["Pitta"], "tip": "Boosts immunity."},
    "bay leaf": {"energy": "Hot", "good_for": ["Kapha", "Vata"], "bad_for": ["Pitta"], "tip": "Digestive spice."},
    "betel leaf": {"energy": "Hot", "good_for": ["Kapha"], "bad_for": ["Pitta"], "tip": "Stimulant."},
    "bibhitaki": {"energy": "Hot", "good_for": ["Kapha"], "bad_for": ["Vata"], "tip": "Throat health."},
    "bitter gourd": {"energy": "Cold", "good_for": ["Pitta", "Kapha"], "bad_for": ["Vata"], "tip": "Lowers blood sugar."},
    "black pepper": {"energy": "Hot", "good_for": ["Kapha"], "bad_for": ["Pitta"], "tip": "Clears mucus instantly."},
    "black salt": {"energy": "Hot", "good_for": ["Vata"], "bad_for": ["Pitta"], "tip": "Improves appetite."},
    "brahmi": {"energy": "Cooling", "good_for": ["Pitta", "Vata"], "bad_for": ["Kapha"], "tip": "Brain tonic."},
    "bhringraj": {"energy": "Hot", "good_for": ["Vata", "Kapha"], "bad_for": ["Pitta"], "tip": "Hair growth."},

    # --- C ---
    "camphor": {"energy": "Cooling", "good_for": ["Pitta", "Kapha"], "bad_for": ["Vata"], "tip": "Respiratory aid."},
    "cardamom": {"energy": "Cooling", "good_for": ["Pitta", "Vata"], "bad_for": [], "tip": "Stops nausea."},
    "carom": {"energy": "Hot", "good_for": ["Vata", "Kapha"], "bad_for": ["Pitta"], "tip": "Gas relief."},
    "cassia": {"energy": "Hot", "good_for": ["Kapha"], "bad_for": ["Pitta"], "tip": "Antifungal."},
    "castor": {"energy": "Hot", "good_for": ["Vata"], "bad_for": ["Pitta"], "tip": "Strong purgative."},
    "catechu": {"energy": "Cold", "good_for": ["Pitta", "Kapha"], "bad_for": ["Vata"], "tip": "Oral health."},
    "chamomile": {"energy": "Cooling", "good_for": ["Pitta"], "bad_for": ["Kapha"], "tip": "Calming tea."},
    "chickpea": {"energy": "Dry", "good_for": ["Kapha"], "bad_for": ["Vata"], "tip": "Drying protein."},
    "chili": {"energy": "Hot", "good_for": ["Kapha"], "bad_for": ["Pitta"], "tip": "Increases internal heat."},
    "chirata": {"energy": "Cold", "good_for": ["Pitta", "Kapha"], "bad_for": ["Vata"], "tip": "Bitter tonic for fever."},
    "chitrak": {"energy": "Hot", "good_for": ["Kapha"], "bad_for": ["Pitta"], "tip": "Increases digestive fire."},
    "cinnamon": {"energy": "Hot", "good_for": ["Vata", "Kapha"], "bad_for": ["Pitta"], "tip": "Improves circulation."},
    "clove": {"energy": "Hot", "good_for": ["Kapha"], "bad_for": ["Pitta"], "tip": "Toothache relief."},
    "coconut": {"energy": "Cold", "good_for": ["Pitta"], "bad_for": ["Kapha"], "tip": "Nutritive and cooling."},
    "coriander": {"energy": "Cold", "good_for": ["Pitta"], "bad_for": ["Vata"], "tip": "Cooling digestive."},
    "cumin": {"energy": "Hot", "good_for": ["Vata", "Kapha"], "bad_for": ["Pitta"], "tip": "Standard digestive."},
    "curry leaf": {"energy": "Warm", "good_for": ["Kapha"], "bad_for": ["Pitta"], "tip": "Prevents greying."},

    # --- D - G ---
    "dandelion": {"energy": "Cold", "good_for": ["Pitta"], "bad_for": ["Vata"], "tip": "Liver detox."},
    "daruharidra": {"energy": "Hot", "good_for": ["Kapha"], "bad_for": ["Pitta"], "tip": "Eye infections."},
    "dates": {"energy": "Cold", "good_for": ["Vata", "Pitta"], "bad_for": ["Kapha"], "tip": "Instant energy."},
    "dill": {"energy": "Hot", "good_for": ["Vata", "Kapha"], "bad_for": ["Pitta"], "tip": "Colic relief."},
    "drumstick": {"energy": "Hot", "good_for": ["Kapha", "Vata"], "bad_for": ["Pitta"], "tip": "Mineral rich."},
    "eucalyptus": {"energy": "Hot", "good_for": ["Kapha"], "bad_for": ["Pitta"], "tip": "Decongestant."},
    "fennel": {"energy": "Cold", "good_for": ["Pitta", "Vata"], "bad_for": [], "tip": "Safe for all ages."},
    "fenugreek": {"energy": "Hot", "good_for": ["Vata", "Kapha"], "bad_for": ["Pitta"], "tip": "Controls diabetes."},
    "flaxseed": {"energy": "Hot", "good_for": ["Vata"], "bad_for": ["Pitta"], "tip": "Omega 3 source."},
    "garlic": {"energy": "Very Hot", "good_for": ["Vata", "Kapha"], "bad_for": ["Pitta"], "tip": "Heart health; avoid in acidity."},
    "ginger": {"energy": "Hot", "good_for": ["Vata", "Kapha"], "bad_for": ["Pitta"], "tip": "Universal medicine."},
    "gokshura": {"energy": "Cold", "good_for": ["Pitta", "Vata"], "bad_for": ["Kapha"], "tip": "Kidney tonic."},
    "gotu kola": {"energy": "Cold", "good_for": ["Pitta"], "bad_for": ["Vata"], "tip": "Memory aid."},
    "guduchi": {"energy": "Warm", "good_for": ["Tridosha"], "bad_for": [], "tip": "Best immunity booster."},
    "guggulu": {"energy": "Hot", "good_for": ["Vata", "Kapha"], "bad_for": ["Pitta"], "tip": "Lowers cholesterol."},
    "gymnema": {"energy": "Cooling", "good_for": ["Pitta", "Kapha"], "bad_for": ["Vata"], "tip": "Sugar destroyer (Gudmar)."},

    # --- H - M ---
    "haritaki": {"energy": "Warm", "good_for": ["Tridosha"], "bad_for": [], "tip": "Mild laxative."},
    "henna": {"energy": "Cold", "good_for": ["Pitta"], "bad_for": ["Vata"], "tip": "Cooling dye."},
    "hibiscus": {"energy": "Cold", "good_for": ["Pitta"], "bad_for": ["Kapha"], "tip": "Hair conditioner."},
    "hing": {"energy": "Hot", "good_for": ["Vata", "Kapha"], "bad_for": ["Pitta"], "tip": "Anti-bloating."},
    "honey": {"energy": "Warm", "good_for": ["Kapha"], "bad_for": ["Pitta"], "tip": "Scrapes fat; do not heat."},
    "isabgol": {"energy": "Cold", "good_for": ["Pitta", "Vata"], "bad_for": ["Kapha"], "tip": "Bulk laxative."},
    "jaggery": {"energy": "Hot", "good_for": ["Vata"], "bad_for": ["Pitta"], "tip": "Blood builder."},
    "jamun": {"energy": "Cold", "good_for": ["Pitta", "Kapha"], "bad_for": ["Vata"], "tip": "Diabetes control."},
    "jasmine": {"energy": "Cold", "good_for": ["Pitta"], "bad_for": ["Kapha"], "tip": "Cooling mood lifter."},
    "jatamansi": {"energy": "Cold", "good_for": ["Pitta", "Vata"], "bad_for": ["Kapha"], "tip": "Sleep aid."},
    "kalmegh": {"energy": "Cold", "good_for": ["Pitta", "Kapha"], "bad_for": ["Vata"], "tip": "Liver detox."},
    "kanchanar": {"energy": "Cold", "good_for": ["Pitta", "Kapha"], "bad_for": ["Vata"], "tip": "Thyroid health."},
    "katuki": {"energy": "Cold", "good_for": ["Pitta", "Kapha"], "bad_for": ["Vata"], "tip": "Liver flush."},
    "khadira": {"energy": "Cold", "good_for": ["Pitta", "Kapha"], "bad_for": ["Vata"], "tip": "Skin diseases."},
    "kutaj": {"energy": "Cold", "good_for": ["Pitta", "Kapha"], "bad_for": ["Vata"], "tip": "Stops dysentery."},
    "lemon": {"energy": "Warm", "good_for": ["Vata", "Kapha"], "bad_for": ["Pitta"], "tip": "Digestion stimulant."},
    "licorice": {"energy": "Cold", "good_for": ["Pitta", "Vata"], "bad_for": ["Kapha"], "tip": "Heals ulcers."},
    "lodhra": {"energy": "Cold", "good_for": ["Pitta", "Kapha"], "bad_for": ["Vata"], "tip": "Female tonic."},
    "long pepper": {"energy": "Hot", "good_for": ["Kapha", "Vata"], "bad_for": ["Pitta"], "tip": "Lung rejuvenator."},
    "lotus": {"energy": "Cold", "good_for": ["Pitta"], "bad_for": ["Kapha"], "tip": "Calming."},
    "manjistha": {"energy": "Cold", "good_for": ["Pitta", "Kapha"], "bad_for": ["Vata"], "tip": "Blood purifier."},
    "mint": {"energy": "Cooling", "good_for": ["Pitta"], "bad_for": ["Vata"], "tip": "Nausea relief."},
    "moringa": {"energy": "Hot", "good_for": ["Kapha", "Vata"], "bad_for": ["Pitta"], "tip": "Superfood."},
    "mustard": {"energy": "Hot", "good_for": ["Kapha"], "bad_for": ["Pitta"], "tip": "Heating oil."},

    # --- N - Z ---
    "neem": {"energy": "Cold/Dry", "good_for": ["Pitta", "Kapha"], "bad_for": ["Vata"], "tip": "Strong antiseptic."},
    "nirgundi": {"energy": "Hot", "good_for": ["Vata", "Kapha"], "bad_for": ["Pitta"], "tip": "Pain relief."},
    "nutmeg": {"energy": "Hot", "good_for": ["Vata", "Kapha"], "bad_for": ["Pitta"], "tip": "Sedative in milk."},
    "onion": {"energy": "Hot", "good_for": ["Vata"], "bad_for": ["Pitta"], "tip": "Libido booster."},
    "papaya": {"energy": "Hot", "good_for": ["Kapha", "Vata"], "bad_for": ["Pitta"], "tip": "Digestive enzyme."},
    "pippali": {"energy": "Hot", "good_for": ["Kapha", "Vata"], "bad_for": ["Pitta"], "tip": "Respiratory care."},
    "pomegranate": {"energy": "Warm", "good_for": ["Tridosha"], "bad_for": [], "tip": "Heart and blood tonic."},
    "psyllium": {"energy": "Cold", "good_for": ["Pitta", "Vata"], "bad_for": ["Kapha"], "tip": "Fiber source."},
    "punarnava": {"energy": "Warm", "good_for": ["Kapha", "Vata"], "bad_for": ["Pitta"], "tip": "Kidney renewal."},
    "raisin": {"energy": "Cold", "good_for": ["Pitta", "Vata"], "bad_for": ["Kapha"], "tip": "Cures thirst."},
    "rasna": {"energy": "Hot", "good_for": ["Vata", "Kapha"], "bad_for": ["Pitta"], "tip": "Back pain specialist."},
    "rose": {"energy": "Cold", "good_for": ["Pitta"], "bad_for": ["Kapha"], "tip": "Heart cooling."},
    "saffron": {"energy": "Hot", "good_for": ["Tridosha"], "bad_for": [], "tip": "Complexion enhancer."},
    "salt": {"energy": "Hot", "good_for": ["Vata"], "bad_for": ["Pitta", "Kapha"], "tip": "Retains water."},
    "sandalwood": {"energy": "Cold", "good_for": ["Pitta"], "bad_for": ["Vata"], "tip": "Prickly heat relief."},
    "sariva": {"energy": "Cold", "good_for": ["Pitta"], "bad_for": ["Kapha"], "tip": "Cooling blood purifier."},
    "senna": {"energy": "Cold", "good_for": ["Pitta", "Kapha"], "bad_for": ["Vata"], "tip": "Strong laxative."},
    "sesame": {"energy": "Hot", "good_for": ["Vata"], "bad_for": ["Pitta"], "tip": "Bone strength."},
    "shallaki": {"energy": "Hot", "good_for": ["Vata", "Kapha"], "bad_for": ["Pitta"], "tip": "Joint health."},
    "shatavari": {"energy": "Cold", "good_for": ["Pitta", "Vata"], "bad_for": ["Kapha"], "tip": "Hormone balance."},
    "shilajit": {"energy": "Hot", "good_for": ["Kapha", "Vata"], "bad_for": ["Pitta"], "tip": "Stamina builder."},
    "shankhpushpi": {"energy": "Cold", "good_for": ["Pitta", "Vata"], "bad_for": ["Kapha"], "tip": "Memory booster."},
    "soapnut": {"energy": "Hot", "good_for": ["Kapha"], "bad_for": ["Pitta"], "tip": "Natural cleaner."},
    "tamarind": {"energy": "Hot", "good_for": ["Vata"], "bad_for": ["Pitta"], "tip": "Digestive sourness."},
    "triphala": {"energy": "Balanced", "good_for": ["Tridosha"], "bad_for": [], "tip": "Daily detox."},
    "tulsi": {"energy": "Hot", "good_for": ["Kapha", "Vata"], "bad_for": ["Pitta"], "tip": "Adaptogen."},
    "turmeric": {"energy": "Warm", "good_for": ["Tridosha"], "bad_for": [], "tip": "Anti-inflammatory."},
    "valerian": {"energy": "Warm", "good_for": ["Vata"], "bad_for": ["Pitta"], "tip": "Sedative."},
    "vasa": {"energy": "Cold", "good_for": ["Pitta", "Kapha"], "bad_for": ["Vata"], "tip": "Bleeding disorders."},
    "vidanga": {"energy": "Hot", "good_for": ["Kapha", "Vata"], "bad_for": ["Pitta"], "tip": "Worms."},
    "vijaysar": {"energy": "Cold", "good_for": ["Pitta", "Kapha"], "bad_for": ["Vata"], "tip": "Diabetes cup."},
    "walnut": {"energy": "Hot", "good_for": ["Vata"], "bad_for": ["Pitta"], "tip": "Brain food."},
    "wheatgrass": {"energy": "Cold", "good_for": ["Pitta", "Kapha"], "bad_for": ["Vata"], "tip": "Blood builder."},
    "wintergreen": {"energy": "Hot", "good_for": ["Kapha"], "bad_for": ["Pitta"], "tip": "Pain oil."},
    "yashtimadhu": {"energy": "Cold", "good_for": ["Pitta", "Vata"], "bad_for": ["Kapha"], "tip": "Voice quality."}
}

# ==========================================
# 3. MASSIVE MEDICAL DB (400+ ENTRIES)
# ==========================================
BACKUP_MEDICAL_DB = {
    # --- 1. RESPIRATORY (50+) ---
    "cough": ["Respiratory", "Tulsi Tea", "Drink warm."],
    "dry cough": ["Respiratory", "Licorice", "Chew stick."],
    "wet cough": ["Respiratory", "Vasa", "Leaf juice."],
    "chronic cough": ["Respiratory", "Kantakari", "Decoction."],
    "whooping cough": ["Respiratory", "Ginger", "Juice with honey."],
    "asthma": ["Respiratory", "Bharangi", "Root powder."],
    "bronchitis": ["Respiratory", "Pushkarmool", "Honey paste."],
    "acute bronchitis": ["Respiratory", "Vasa", "Juice."],
    "chronic bronchitis": ["Respiratory", "Somlata", "Powder."],
    "breathlessness": ["Respiratory", "Camphor", "Inhale."],
    "common cold": ["Respiratory", "Ginger", "Tea."],
    "head cold": ["Respiratory", "Black Pepper", "Milk."],
    "chest cold": ["Respiratory", "Mustard Oil", "Rub."],
    "running nose": ["Respiratory", "Vacha", "Inhale."],
    "blocked nose": ["Respiratory", "Eucalyptus", "Steam."],
    "sinusitis": ["Respiratory", "Shadbindu Oil", "Nasya."],
    "frontal sinusitis": ["Respiratory", "Ginger", "Paste on head."],
    "sore throat": ["Respiratory", "Turmeric", "Gargle."],
    "strep throat": ["Respiratory", "Neem", "Gargle."],
    "hoarseness": ["Respiratory", "Khadira", "Chew."],
    "laryngitis": ["Respiratory", "Licorice", "Chew."],
    "tonsillitis": ["Respiratory", "Salt Water", "Gargle."],
    "allergic rhinitis": ["Respiratory", "Haridra", "Milk."],
    "hay fever": ["Respiratory", "Guduchi", "Powder."],
    "dust allergy": ["Respiratory", "Tulsi", "Daily."],
    "pollen allergy": ["Respiratory", "Neem", "Leaf."],
    "pneumonia": ["Respiratory", "Garlic", "Milk."],
    "tuberculosis": ["Respiratory", "Garlic", "Daily."],
    "hiccups": ["Respiratory", "Cardamom", "Chew."],
    "sneezing": ["Respiratory", "Ginger", "Tea."],
    "snoring": ["Respiratory", "Ghee", "Nasal drops."],
    
    # --- 2. DIGESTIVE (60+) ---
    "indigestion": ["Digestive", "Ginger+Salt", "Eat."],
    "dyspepsia": ["Digestive", "Cumin", "Water."],
    "acid dyspepsia": ["Digestive", "Amla", "Powder."],
    "constipation": ["Digestive", "Triphala", "Warm water."],
    "chronic constipation": ["Digestive", "Castor Oil", "Milk."],
    "gas": ["Digestive", "Hing", "Warm water."],
    "flatulence": ["Digestive", "Ajwain", "Chew."],
    "bloating": ["Digestive", "Fennel", "Tea."],
    "acidity": ["Digestive", "Amla", "Juice."],
    "heartburn": ["Digestive", "Coriander", "Water."],
    "gerd": ["Digestive", "Shatavari", "Milk."],
    "acid reflux": ["Digestive", "Cold Milk", "Sip."],
    "piles": ["Digestive", "Buttermilk", "Drink."],
    "bleeding piles": ["Digestive", "Nagakeshar", "Butter."],
    "fissure": ["Digestive", "Jatyadi Ghrita", "Apply."],
    "diarrhea": ["Digestive", "Pomegranate", "Peel tea."],
    "dysentery": ["Digestive", "Kutaj", "Bark."],
    "ibs": ["Digestive", "Bilva", "Fruit."],
    "colitis": ["Digestive", "Licorice", "Water."],
    "peptic ulcer": ["Digestive", "Amla", "Juice."],
    "gastric ulcer": ["Digestive", "Banana", "Eat."],
    "vomiting": ["Digestive", "Cardamom", "Chew."],
    "nausea": ["Digestive", "Ginger", "Chew."],
    "morning sickness": ["Digestive", "Lemon", "Smell."],
    "travel sickness": ["Digestive", "Ginger", "Hold in mouth."],
    "stomach pain": ["Digestive", "Dill", "Chew."],
    "colic": ["Digestive", "Hing", "Navel."],
    "worm infestation": ["Digestive", "Vidanga", "Honey."],
    "pinworms": ["Digestive", "Vidanga", "Powder."],
    "tapeworms": ["Digestive", "Pumpkin Seeds", "Eat."],
    "loss of appetite": ["Digestive", "Chitrak", "Powder."],
    "thirst": ["Digestive", "Vetiver", "Water."],
    "food poisoning": ["Digestive", "Charcoal", "Consult."],
    
    # --- 3. LIVER & METABOLIC (40+) ---
    "jaundice": ["Liver", "Bhumyamalaki", "Plant juice."],
    "hepatitis": ["Liver", "Kalmegh", "Decoction."],
    "fatty liver": ["Liver", "Aloe Vera", "Juice."],
    "liver cirrhosis": ["Liver", "Punarnava", "Support."],
    "gallstones": ["Liver", "Pashanbheda", "Tea."],
    "diabetes": ["Metabolic", "Karela", "Juice."],
    "diabetes type 2": ["Metabolic", "Turmeric+Amla", "Mix."],
    "high blood sugar": ["Metabolic", "Gudmar", "Chew."],
    "obesity": ["Metabolic", "Honey+Water", "Morning."],
    "weight gain": ["Metabolic", "Banana", "Milk."],
    "thyroid": ["Metabolic", "Coriander", "Water."],
    "hypothyroid": ["Metabolic", "Kanchanar", "Guggulu."],
    "hyperthyroid": ["Metabolic", "Shankhpushpi", "Syrup."],
    "high cholesterol": ["Metabolic", "Garlic", "Raw."],
    "high triglycerides": ["Metabolic", "Arjuna", "Tea."],
    "uric acid": ["Metabolic", "Giloy", "Juice."],
    "gout": ["Metabolic", "Guduchi", "Stem."],
    
    # --- 4. JOINTS & BONES (50+) ---
    "arthritis": ["Joints", "Nirgundi", "Oil."],
    "osteoarthritis": ["Joints", "Shallaki", "Resin."],
    "rheumatoid arthritis": ["Joints", "Castor Oil", "Drink."],
    "back pain": ["Joints", "Mahanarayan Oil", "Rub."],
    "sciatica": ["Nerves", "Rasna", "Tea."],
    "spondylitis": ["Joints", "Ashwagandha", "Daily."],
    "cervical spondylosis": ["Joints", "Greeva Basti", "Therapy."],
    "frozen shoulder": ["Joints", "Nasya", "Drops."],
    "knee pain": ["Joints", "Castor Leaf", "Wrap."],
    "knee swelling": ["Joints", "Turmeric", "Paste."],
    "osteoporosis": ["Bones", "Sesame", "Chew."],
    "weak bones": ["Bones", "Praval", "Calcium."],
    "fracture": ["Bones", "Cissus", "Paste."],
    "sprain": ["Muscles", "Tamarind Leaf", "Paste."],
    "muscle cramp": ["Muscles", "Salt", "Water."],
    "muscle pain": ["Muscles", "Wintergreen", "Oil."],
    "fibromyalgia": ["Muscles", "Ashwagandha", "Milk."],
    "heel pain": ["Joints", "Calotropis", "Warm leaf."],
    "tennis elbow": ["Joints", "Ice/Heat", "Alternate."],
    
    # --- 5. SKIN (60+) ---
    "acne": ["Skin", "Neem", "Paste."],
    "pimples": ["Skin", "Sandalwood", "Paste."],
    "scars": ["Skin", "Kumkumadi", "Oil."],
    "eczema": ["Skin", "Manjistha", "Tea."],
    "psoriasis": ["Skin", "Wrightia", "Oil."],
    "ringworm": ["Skin", "Cassia", "Paste."],
    "athlete's foot": ["Skin", "Neem", "Wash."],
    "fungal infection": ["Skin", "Garlic", "Paste."],
    "itching": ["Skin", "Coconut Oil", "Apply."],
    "hives": ["Skin", "Baking Soda", "Bath."],
    "vitiligo": ["Skin", "Bakuchi", "Oil."],
    "dark circles": ["Skin", "Cucumber", "Slice."],
    "pigmentation": ["Skin", "Potato", "Juice."],
    "sunburn": ["Skin", "Aloe Vera", "Cold."],
    "wrinkles": ["Skin", "Almond Oil", "Massage."],
    "dry skin": ["Skin", "Sesame Oil", "Rub."],
    "oily skin": ["Skin", "Multani Mitti", "Pack."],
    "cracked heels": ["Skin", "Castor Oil", "Apply."],
    "burns": ["Skin", "Ghee", "Apply."],
    "minor cuts": ["Skin", "Turmeric", "Powder."],
    "corns": ["Skin", "Garlic", "Bandage."],
    "warts": ["Skin", "Fig Latex", "Drop."],
    "boils": ["Skin", "Neem", "Poultice."],
    
    # --- 6. HAIR (30+) ---
    "hair fall": ["Hair", "Bhringraj", "Oil."],
    "severe hair fall": ["Hair", "Onion", "Juice."],
    "baldness": ["Hair", "Bhringraj", "Daily."],
    "dandruff": ["Hair", "Lemon", "Rub."],
    "gray hair": ["Hair", "Amla", "Eat."],
    "premature graying": ["Hair", "Curry Leaves", "Eat."],
    "split ends": ["Hair", "Almond Oil", "Tips."],
    "dry hair": ["Hair", "Hibiscus", "Wash."],
    "lice": ["Hair", "Custard Apple", "Seed paste."],
    "thin hair": ["Hair", "Castor Oil", "Mix."],
    
    # --- 7. NERVOUS & MENTAL (40+) ---
    "stress": ["Mental", "Ashwagandha", "Milk."],
    "anxiety": ["Mental", "Brahmi", "Tea."],
    "panic attack": ["Mental", "Deep Breathe", "Pranayama."],
    "depression": ["Mental", "Jatamansi", "Smell."],
    "insomnia": ["Mental", "Nutmeg", "Milk."],
    "memory loss": ["Mental", "Shankhpushpi", "Syrup."],
    "concentration": ["Mental", "Brahmi", "Ghee."],
    "headache": ["Head", "Ginger", "Paste."],
    "migraine": ["Head", "Godanti", "Mix."],
    "vertigo": ["Head", "Amla", "Water."],
    "dizziness": ["Head", "Raisin", "Water."],
    "epilepsy": ["Nerves", "Vacha", "Ghee."],
    "paralysis": ["Nerves", "Bala", "Oil."],
    "tremors": ["Nerves", "Kaunch", "Seeds."],
    "parkinson's": ["Nerves", "Mucuna", "Powder."],
    "alzheimer's": ["Nerves", "Turmeric", "Daily."],
    
    # --- 8. HEART & BLOOD (25+) ---
    "high bp": ["Heart", "Sarpagandha", "Consult."],
    "hypertension": ["Heart", "Arjuna", "Tea."],
    "low bp": ["Heart", "Coffee", "Drink."],
    "palpitations": ["Heart", "Rose", "Jam."],
    "angina": ["Heart", "Arjuna", "Milk."],
    "anemia": ["Blood", "Pomegranate", "Eat."],
    "nose bleed": ["Blood", "Cold Water", "Head."],
    "varicose veins": ["Blood", "Gotu Kola", "Cream."],
    
    # --- 9. MEN & WOMEN (40+) ---
    "menstrual pain": ["Women", "Ashoka", "Bark."],
    "heavy period": ["Women", "Lodhra", "Powder."],
    "irregular period": ["Women", "Aloe Vera", "Pulp."],
    "pcos": ["Women", "Kanchanar", "Guggulu."],
    "white discharge": ["Women", "Rice Water", "Drink."],
    "menopause": ["Women", "Shatavari", "Root."],
    "hot flashes": ["Women", "Shatavari", "Cooling."],
    "low libido": ["Men", "Ashwagandha", "Root."],
    "sexual weakness": ["Men", "Shilajit", "Resin."],
    "premature ejaculation": ["Men", "Nutmeg", "Milk."],
    "erectile dysfunction": ["Men", "Gokshura", "Fruit."],
    "sperm count": ["Men", "Safed Musli", "Milk."],
    "prostate": ["Men", "Varuna", "Bark."],
    
    # --- 10. URINARY (20+) ---
    "kidney stones": ["Urinary", "Pashanbheda", "Tea."],
    "burning urine": ["Urinary", "Coriander", "Water."],
    "uti": ["Urinary", "Cranberry", "Juice."],
    "bed wetting": ["Urinary", "Cinnamon", "Chew."],
    "incontinence": ["Urinary", "Sesame", "Chew."],
    "fluid retention": ["Urinary", "Barley", "Water."],
    
    # --- 11. GENERAL (30+) ---
    "fever": ["General", "Giloy", "Tea."],
    "viral fever": ["General", "Tulsi", "Tea."],
    "malaria": ["General", "Kiratatikta", "Tea."],
    "typhoid": ["General", "Muktashukti", "Calcium."],
    "dengue": ["General", "Papaya Leaf", "Juice."],
    "weakness": ["General", "Dates", "Eat."],
    "fatigue": ["General", "Ashwagandha", "Milk."],
    "heat stroke": ["General", "Raw Mango", "Drink."],
    "hangover": ["General", "Lemon", "Water."],
    "mosquito bite": ["General", "Tulsi", "Rub."],
    "bee sting": ["General", "Iron", "Rub key."],
    "swelling": ["General", "Punarnava", "Tea."],
    
    # --- EAR (10+) ---
    "ear ache": ["Ear", "Garlic Oil", "Drops."],
    "ear infection": ["Ear", "Neem Oil", "Drops."],
    "tinnitus": ["Ear", "Bilva Oil", "Drops."],
    "ringing ears": ["Ear", "Ashwagandha", "Milk."],
    "ear wax": ["Ear", "Mustard Oil", "Drops."],
    "swimmer's ear": ["Ear", "Vinegar", "Wash."],
    "deafness": ["Ear", "Bael", "Oil."],
    "ear discharge": ["Ear", "Turmeric", "Milk."],
    
    # --- EYE (10+) ---
    "eye pain": ["Eye", "Rose Water", "Drops."],
    "burning eyes": ["Eye", "Coriander", "Wash."],
    "conjunctivitis": ["Eye", "Triphala", "Wash."],
    "stye": ["Eye", "Turmeric", "Paste."],
    "dry eyes": ["Eye", "Ghee", "Eyelids."],
    "weak eyesight": ["Eye", "Amla", "Eat."],
    "night blindness": ["Eye", "Moringa", "Leaf."],
    "cataract": ["Eye", "Triphala", "Ghrita."],
    "red eyes": ["Eye", "Sandalwood", "Paste."]
}

def load_data():
    """Loads CSVs and merges them into the Global DBs"""
    global HERB_DETAILS_DB, MEDICAL_DB
    
    # 1. Initialize with Backup Data
    MEDICAL_DB = BACKUP_MEDICAL_DB.copy()

    # 2. Load Herb Info (Ayurvedic Medicines.csv)
    if os.path.exists(HERB_INFO_CSV):
        try:
            with open(HERB_INFO_CSV, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    clean_row = {k.strip(): v.strip() for k, v in row.items() if k}
                    HERB_DETAILS_DB.append(clean_row)
            print(f"✅ Loaded {len(HERB_DETAILS_DB)} herb details from {HERB_INFO_CSV}")
        except Exception as e:
            print(f"❌ Error loading Herb CSV: {e}")

    # 3. Load Remedies (Medicinal Plants.csv)
    if os.path.exists(REMEDY_CSV):
        try:
            with open(REMEDY_CSV, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                count = 0
                for row in reader:
                    r = {k.strip(): v.strip() for k, v in row.items() if k}
                    disease = r.get('disease', '').strip().lower()
                    plant = r.get('plant_name', '').strip()
                    usage = r.get('how_to_use', '').strip()
                    
                    if disease and plant:
                        # Merge with existing logic
                        if disease in MEDICAL_DB:
                            # Append to existing
                            old_cat, old_plant, old_use = MEDICAL_DB[disease]
                            MEDICAL_DB[disease] = [old_cat, f"{old_plant}, {plant}", f"{old_use} <br>OR<br> {plant}: {usage}"]
                        else:
                            MEDICAL_DB[disease] = ["General", plant, usage]
                        count += 1
            print(f"✅ Loaded {count} remedies from {REMEDY_CSV}")
        except Exception as e:
            print(f"❌ Error loading Remedy CSV: {e}")

# Load data immediately
load_data()

# ==========================================
# 4. ANALYSIS DB (Body Types)
# ==========================================
ANALYSIS_DB = {
    "Vata": { "title": "🍃 Vata (Air)", "desc": "Dry, Cold, Light. You need Warmth.", "bad": "Raw Salads, Cold Drinks", "good": "Sesame Oil, Ginger" },
    "Pitta": { "title": "🔥 Pitta (Fire)", "desc": "Hot, Sharp, Oily. You need Cooling.", "bad": "Chili, Sour Yogurt", "good": "Ghee, Coconut" },
    "Kapha": { "title": "💧 Kapha (Earth)", "desc": "Heavy, Cold, Stable. You need Stimulation.", "bad": "Cheese, Sweets", "good": "Spices, Honey" }
}


# ==========================================
# 6. BACKEND LOGIC
# ==========================================

def get_dosha_score(text):
    text = text.lower()
    vata = sum(1 for w in ["thin", "dry", "cold", "light", "anxious", "gas", "constipation"] if w in text)
    pitta = sum(1 for w in ["hot", "sweat", "red", "anger", "acidity", "sharp", "sensitive"] if w in text)
    kapha = sum(1 for w in ["heavy", "slow", "oily", "mucus", "sleep", "weight", "sweet"] if w in text)
    if vata + pitta + kapha == 0: return None
    scores = {"Vata": vata, "Pitta": pitta, "Kapha": kapha}
    return max(scores, key=scores.get)

def check_herb_reaction(herb_text, dosha):
    if not dosha: return ""
    found_herb = None
    for key in HERB_REACTION_DB:
        if key in herb_text.lower():
            found_herb = key; break
    if not found_herb: return ""
    data = HERB_REACTION_DB[found_herb]
    
    if dosha in data['bad_for']:
        return f"<div class='alert-box'>⚠️ <b>Caution for {dosha}:</b> {found_herb.title()} is {data['energy']}. {data['tip']}</div>"
    elif dosha in data['good_for']:
        return f"<div class='safe-box'>✅ <b>Great for {dosha}:</b> {found_herb.title()} is {data['energy']}. {data['tip']}</div>"
    return ""

def get_wiki_data(query):
    # 1. Clean the query
    clean_query = query.replace("plant", "").replace("info", "").replace("about", "").replace("what is", "").replace("remedy for", "").strip()
    
    headers = {'User-Agent': 'HerbalBot/3.0'}
    
    # 2. STRICT KEYWORDS (Only these topics pass)
    VALID_KEYWORDS = [
        "plant", "herb", "tree", "shrub", "flower", "leaf", "root", "seed", "fruit", "bark", "stem", 
        "species", "family", "genus", "botany", "botanical", "evergreen", "deciduous",
        "disease", "syndrome", "disorder", "infection", "virus", "bacteria", "fungus", 
        "symptom", "pain", "inflammation", "fever", "cough", "health", "medicine", "medical", 
        "therapy", "treatment", "ayurveda", "homeopathy", "vitamin", "nutrient", "anatomy", "body"
    ]

    try:
        # 3. Search Wikipedia
        search_url = "https://en.wikipedia.org/w/api.php"
        params = {"action": "opensearch", "search": clean_query, "limit": "1", "format": "json"}
        results = requests.get(search_url, params=params, headers=headers, timeout=3).json()
        
        if not results[1]: return "", "", ""
        title = results[1][0]
        
        # 4. Get Summary
        summary_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
        data = requests.get(summary_url, headers=headers, timeout=3).json()
        
        desc = data.get("extract", "")
        img = data.get("thumbnail", {}).get("source", "")
        
        # 5. STRICT FILTER: Check if keywords exist in description
        if any(word in desc.lower() for word in VALID_KEYWORDS):
            if not img: img = "https://cdn-icons-png.flaticon.com/512/628/628283.png"
            return title, img, desc
        else:
            return "", "", "" # Return nothing if it's not a plant/disease
            
    except:
        return "", "", ""

@app.route("/chatbot")
def chatbot_page():
    return render_template("chatbot.html")

@app.route("/chat", methods=["POST"])
def chat():
    msg = request.form.get("msg", "").strip().lower()
    current_dosha = request.form.get("dosha")

    # -----------------------------
    # 1. DOSHA DETECTION
    # -----------------------------
    new_dosha = get_dosha_score(msg)
    if new_dosha:
        current_dosha = new_dosha
        info = ANALYSIS_DB[new_dosha]
        html = f"""
        <b>Type Detected: {info['title']}</b><br>
        {info['desc']}<br>
        <div class='alert-box'>🚫 Avoid: {info['bad']}</div>
        <div class='safe-box'>✅ Favor: {info['good']}</div>
        """
        return {
            "html": html,
            "speech": f"You seem to be {new_dosha}. {info['desc']}",
            "dosha": current_dosha
        }

    # -----------------------------
    # 2. PLANT INFO FROM CSV (FIXED)
    # -----------------------------
    for row in HERB_DETAILS_DB:
        common = row.get("Common Name", "").lower()
        latin = row.get("Latin Name", "").lower()
        synonyms = row.get("Synonyms", "").lower()

        if common and common in msg or latin and latin in msg or synonyms and any(s.strip() in msg for s in synonyms.split(",")):
            html = f"""
            <b>🌿 {row['Common Name']}</b> ({row['Latin Name']})<br>
            <b>Main Action:</b> {row.get('Main Action','')}<br>
            <b>Uses:</b> {row.get('Therapeutic Uses','')}<br>
            <span style='font-size:0.8rem'>
            <b>Potency:</b> {row.get('Potency','')} |
            <b>Taste:</b> {row.get('Taste','')}
            </span>
            """
            return {
                "html": html,
                "speech": f"{row['Common Name']} is used for {row.get('Therapeutic Uses','')}",
                "dosha": current_dosha
            }

    # -----------------------------
    # 3. HERB REACTION DB
    # -----------------------------
    for herb, data in HERB_REACTION_DB.items():
        if herb in msg:
            reaction_html = check_herb_reaction(herb, current_dosha)
            html = f"""
            <b>🌿 Herb: {herb.title()}</b><br>
            🔥 <b>Energy:</b> {data['energy']}<br>
            ✅ <b>Good for:</b> {', '.join(data['good_for'])}<br>
            ⚠️ <b>Caution for:</b> {', '.join(data['bad_for'])}
            {reaction_html}
            """
            return {
                "html": html,
                "speech": f"{herb.title()} is {data['energy']}. {data['tip']}",
                "dosha": current_dosha
            }

    # -----------------------------
    # 4. MEDICAL REMEDY SEARCH
    # -----------------------------
    found_key = None
    for key in MEDICAL_DB:
        if key in msg:
            found_key = key
            break

    if not found_key:
        matches = get_close_matches(msg, MEDICAL_DB.keys(), n=1, cutoff=0.75)
        if matches:
            found_key = matches[0]

    if found_key:
        cat, plant, use = MEDICAL_DB[found_key]
        reaction_html = check_herb_reaction(plant, current_dosha)
        html = f"""
        <b>Condition:</b> {found_key.title()} ({cat})<br>
        🌿 <b>Remedy:</b> {plant}<br>
        🥣 <b>Usage:</b> {use}
        {reaction_html}
        """
        return {
            "html": html,
            "speech": f"For {found_key}, use {plant}.",
            "dosha": current_dosha
        }

    # -----------------------------
    # 5. WIKIPEDIA FALLBACK
    # -----------------------------
    title, img, desc = get_wiki_data(msg)
    if desc:
        html = f"""
        <img src="{img}" style="width:100%; border-radius:10px;">
        <h3>🌿 {title}</h3>
        <p>{desc}</p>
        <small>Source: Wikipedia</small>
        """
        return {
            "html": html,
            "speech": desc.split(".")[0],
            "dosha": current_dosha
        }

    # -----------------------------
    # 6. FINAL FALLBACK
    # -----------------------------
    return {
        "html": "❌ I couldn’t find that. Try <b>'Aloe vera plant info'</b> or <b>'Remedy for cough'</b>.",
        "speech": "No information found.",
        "dosha": current_dosha
    }

# ---------- RUN ----------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
