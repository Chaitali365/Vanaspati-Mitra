from flask import Blueprint, render_template, request, redirect, url_for, flash
import random

# =========================================================
# BLUEPRINT CONFIG
# =========================================================
vanspati_bp = Blueprint(
    "vanspati",
    __name__,
    template_folder="templates",
    static_folder="static"
)

# =========================================================
# 1. DATABASE (IN-MEMORY)
# =========================================================

therapies_db = [
    {
        "id": 1, "name": "Vamana", "type": "Therapeutic Emesis", "dosha": "Kapha",
        "dosha_desc": "Best for Kapha (Heavy/Oily Body Type)",
        "price": 4500, "duration": "15 Days",
        "desc": "Controlled vomiting to eliminate deep-seated mucus toxins from the respiratory tract.",
        "diseases": ["Asthma", "Bronchitis", "Obesity", "Thyroid", "Skin Allergies", "Cold & Cough", "Hay Fever", "Indigestion"],
        "procedure": ["Deep Oleation (Snehana).", "Sweating (Swedana).", "Emetic herbs administration."],
        "benefits": "Clears chest congestion, weight loss, improved digestion.",
        "contra": "Heart patients, Pregnant women, Children, Hypertension.",
        "icon": "🤮"
    },
    {
        "id": 2, "name": "Virechana", "type": "Therapeutic Purgation", "dosha": "Pitta",
        "dosha_desc": "Best for Pitta (Heat/Athletic Body Type)",
        "price": 5000, "duration": "10 Days",
        "desc": "Medicated purgation to cleanse the liver, gallbladder, and small intestine.",
        "diseases": ["Jaundice", "Acidity", "Psoriasis", "Diabetes", "Liver Disorders", "Gastritis", "Skin Allergies", "Eczema", "Acne"],
        "procedure": ["Ghee intake (5 days).", "Massage & Steam.", "Purgative herbs intake."],
        "benefits": "Detoxifies liver, reduces body heat, clears skin.",
        "contra": "Weak digestion, Rectal bleeding, Diarrhea.",
        "icon": "🚽"
    },
    {
        "id": 3, "name": "Basti", "type": "Medicated Enema", "dosha": "Vata",
        "dosha_desc": "Best for Vata (Lean/Dry Body Type)",
        "price": 3000, "duration": "8 Days",
        "desc": "The 'Mother of All Treatments'. Cleanses the colon using herbal decoctions.",
        "diseases": ["Arthritis", "Paralysis", "Constipation", "Back Pain", "Sciatica", "Joint Pain", "Rheumatism", "IBS"],
        "procedure": ["Local Massage.", "Niruha (Decoction) enema.", "Anuvasana (Oil) enema."],
        "benefits": "Lubricates joints, cures neurological disorders.",
        "contra": "Acute fever, Diarrhea, Intestinal obstruction.",
        "icon": "🧴"
    },
    {
        "id": 4, "name": "Nasya", "type": "Nasal Instillation", "dosha": "Kapha",
        "dosha_desc": "Balances Kapha in Head Region",
        "price": 1500, "duration": "7 Days",
        "desc": "Administration of medicated drops through nostrils for head & neck care.",
        "diseases": ["Migraine", "Sinusitis", "Hair Fall", "Insomnia", "Frozen Shoulder", "Vision Problems", "Headache"],
        "procedure": ["Face Massage.", "Mild Steam.", "Herbal drops installation."],
        "benefits": "Clears sinuses, improves vision, relieves headache.",
        "contra": "Pregnancy, Immediately after bath, Flu.",
        "icon": "👃"
    },
    {
        "id": 5, "name": "Raktamokshana", "type": "Blood Letting", "dosha": "Pitta",
        "dosha_desc": "Best for Blood Toxicity",
        "price": 2000, "duration": "1 Day",
        "desc": "Purification of impure blood using Leeches (Jalauka).",
        "diseases": ["Eczema", "Varicose Veins", "Gout", "Hypertension", "Acne", "Herpes", "Abscess", "Psoriasis"],
        "procedure": ["Cleaning area.", "Leech application.", "Dressing."],
        "benefits": "Reduces inflammation, cures skin diseases.",
        "contra": "Anemia, Low BP, Pregnancy.",
        "icon": "🩸"
    },
    {
        "id": 6, "name": "Shirodhara", "type": "Stress Care", "dosha": "Vata",
        "dosha_desc": "Calms the Mind",
        "price": 2500, "duration": "45 Mins",
        "desc": "Continuous pouring of warm medicated oil on the forehead.",
        "diseases": ["Anxiety", "Depression", "Stress", "ADHD", "Memory Loss", "Headache", "Insomnia", "Mental Fatigue"],
        "procedure": ["Lying on Droni.", "Rhythmic Oil pouring.", "Head Massage."],
        "benefits": "Deep relaxation, improved sleep, mental clarity.",
        "contra": "Brain tumor, Neck injury, Open wounds on head.",
        "icon": "💆"
    },
    {
        "id": 7, "name": "Udvartana", "type": "Weight Loss", "dosha": "Kapha",
        "dosha_desc": "Reduces Fat & Heaviness",
        "price": 2200, "duration": "60 Mins",
        "desc": "Deep tissue massage using dry herbal powders to burn fat.",
        "diseases": ["Obesity", "Cellulite", "Lethargy", "High Cholesterol", "Excess Sweating", "Diabetes"],
        "procedure": ["Herbal powder paste.", "Friction massage.", "Steam bath."],
        "benefits": "Burns fat, tones muscles, reduces cellulite.",
        "contra": "Dry skin, Eczema, Psoriasis.",
        "icon": "🌿"
    },
    { "id": 8, "name": "Janu Basti", "type": "Knee Therapy", "dosha": "Vata", "dosha_desc": "Relieves Dryness & Pain in Joints", "price": 1800, "duration": "45 Mins", "desc": "A localized treatment where warm medicated oil is pooled over the knee joint using a dough ring.", "diseases": ["Osteoarthritis", "Knee Strain", "Ligament Tear", "Stiff Joints", "Degenerative Changes", "Cracking Joints"], "procedure": ["Dough ring preparation.", "Oil pooling (Swedana).", "Gentle massage."], "benefits": "Lubricates the knee joint, improves mobility, and reduces pain.", "contra": "Knee fractures, Acute inflammation, Skin infections on knees.", "icon": "🦵" }, { "id": 9, "name": "Kati Basti", "type": "Back Care", "dosha": "Vata", "dosha_desc": "Best for Lumbar Health", "price": 2000, "duration": "45 Mins", "desc": "A specialized treatment for the lower back involving a reservoir of herbal oil over the lumbosacral region.", "diseases": ["Slip Disc", "Sciatica", "Lumbar Spondylosis", "Chronic Backache", "Spinal Compression", "Muscle Spasms"], "procedure": ["Dough dam construction.", "Warm oil retention.", "Local steam."], "benefits": "Strengthens back muscles, relieves nerve compression, and increases flexibility.", "contra": "Fever, Pregnancy, Spinal fractures, Cancerous tumors.", "icon": "🧘" }, { "id": 10, "name": "Netra Tarpana", "type": "Eye Rejuvenation", "dosha": "Pitta", "dosha_desc": "Cools and Soothes the Eyes", "price": 1200, "duration": "30 Mins", "desc": "Medicated ghee is pooled over the eyes to nourish the nervous system and optical tissues.", "diseases": ["Dry Eye Syndrome", "Myopia", "Burning Eyes", "Night Blindness", "Conjunctivitis (Chronic)", "Eye Strain"], "procedure": ["Black gram paste ring around eyes.", "Pouring liquid ghee.", "Controlled blinking exercises."], "benefits": "Improves vision clarity, reduces dark circles, and relaxes the optic nerve.", "contra": "Eye injuries, Active infections, Cataract surgery (Immediate).", "icon": "👁️" }
]

doctors_db = [
    {"id": 101, "name": "Dr. Aarav Sharma", "spec": "M.D. (Ayurveda)", "clinic": "AyurLife Wellness", "city": "Mumbai", "exp": "15 Yrs"},
    {"id": 102, "name": "Dr. Sneha Patil", "spec": "Panchakarma Expert", "clinic": "Green Roots", "city": "Pune", "exp": "12 Yrs"},
    {"id": 103, "name": "Dr. Rajesh Iyer", "spec": "Nadi Vaidya", "clinic": "Veda Cure", "city": "Bangalore", "exp": "20 Yrs"},
    {"id": 104, "name": "Dr. Ananya Das", "spec": "Dermatology (Skin)", "clinic": "Lotus Healing", "city": "Kolkata", "exp": "8 Yrs"},
    {"id": 105, "name": "Dr. Kabir Singh", "spec": "Orthopedic Ayurveda", "clinic": "Bone Care Center", "city": "Delhi", "exp": "18 Yrs"},
    {"id": 106, "name": "Dr. Meera Nair", "spec": "Women's Health", "clinic": "Shakti Clinic", "city": "Kerala", "exp": "14 Yrs"},
    {"id": 107, "name": "Dr. Vikram Malhotra", "spec": "General Medicine", "clinic": "Chennai Ayur", "city": "Chennai", "exp": "10 Yrs"},
    {"id": 108, "name": "Dr. Priya Desai", "spec": "Pediatrics (Balaroga)", "clinic": "Balaji Wellness", "city": "Ahmedabad", "exp": "9 Yrs"},
    {"id": 109, "name": "Dr. Rohan Mehta", "spec": "Neurology", "clinic": "Mind & Body", "city": "Hyderabad", "exp": "22 Yrs"},
    {"id": 110, "name": "Dr. Kavita Verma", "spec": "Skin & Hair", "clinic": "Glow Ayurveda", "city": "Jaipur", "exp": "7 Yrs"},
    {"id": 111, "name": "Dr. Arjun Reddy", "spec": "Sports Medicine", "clinic": "Active Life", "city": "Bangalore", "exp": "11 Yrs"},
    {"id": 112, "name": "Dr. Suresh Pillai", "spec": "Kayachikitsa", "clinic": "Kerala Ayurveda", "city": "Trivandrum", "exp": "25 Yrs"}
]

bookings_db = []
all_diseases = sorted({d for t in therapies_db for d in t["diseases"]})

# =========================================================
# 2. ROUTES
# =========================================================

@vanspati_bp.route("/")
def home():
    return render_template(
        "vanspati/home.html",
        therapies=therapies_db,
        diseases=all_diseases
    )


@vanspati_bp.route("/recommend")
def recommend():
    sel_dosha = request.args.get("dosha")
    sel_disease = request.args.get("disease")

    if sel_disease:
        results = [t for t in therapies_db if sel_disease in t["diseases"]]
    elif sel_dosha:
        results = [t for t in therapies_db if t["dosha"] == sel_dosha]
    else:
        results = therapies_db

    return render_template(
        "vanspati/recommend.html",
        res=results,
        d=sel_dosha or "All",
        dis=sel_disease or "All"
    )


@vanspati_bp.route("/clinics")
def clinics():
    return render_template("vanspati/clinics.html", doctors=doctors_db)


@vanspati_bp.route("/book", methods=["GET", "POST"])
def book():
    if request.method == "POST":
        bid = f"VM-{random.randint(10000, 99999)}"
        bookings_db.append({
            "id": bid,
            "name": request.form["name"],
            "age": request.form["age"],
            "therapy": request.form["therapy"],
            "doctor": request.form["doctor"],
            "date": request.form["date"],
            "status": "Pending"
        })
        flash(f"Booking Sent! ID: {bid}. Awaiting Doctor approval.")
        return redirect(url_for("vanspati.history"))

    return render_template(
        "vanspati/book.html",
        therapies=therapies_db,
        doctors=doctors_db
    )


@vanspati_bp.route("/history")
def history():
    return render_template("vanspati/history.html", bookings=bookings_db)


@vanspati_bp.route("/admin")
def admin():
    revenue = sum(
        t["price"]
        for b in bookings_db if b["status"] == "Confirmed"
        for t in therapies_db if t["name"] == b["therapy"]
    )
    return render_template(
        "vanspati/admin.html",
        bookings=bookings_db,
        doctors=doctors_db,
        revenue=revenue
    )

@vanspati_bp.route("/update/<bid>/<new_status>")
def update_status(bid, new_status):
    for b in bookings_db:
        if b["id"] == bid:
            b["status"] = new_status
            break
    flash(f"Booking {bid} updated to {new_status}")
    return redirect(url_for("vanspati.admin"))