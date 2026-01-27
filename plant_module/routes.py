import os, uuid, psycopg2, requests
from flask import Blueprint, render_template, request, jsonify, url_for
from werkzeug.utils import secure_filename

plant_bp = Blueprint(
    "plant_bp",
    __name__,
    static_folder="assets",      
    template_folder="pages"      
)

# --- CORRECTED PATHING ---
# We use the absolute path of this file to find the 'assets' folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "assets", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

DB_HOST = "localhost"
DB_NAME = "plantdb"
DB_USER = "postgres"
DB_PASS = "root"

API_KEY = "2b10grzENr2nQ4q7k2wVEyc38u"
API_URL = f"https://my-api.plantnet.org/v2/identify/all?api-key={API_KEY}"

def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )

@plant_bp.route("/plant")
def plant_home():
    return render_template("plant_index.html")

@plant_bp.route("/plant/history")
def plant_history():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM plant_logs ORDER BY captured_at DESC")
    plants = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("history.html", plants=plants)

@plant_bp.route("/plant/identify", methods=["POST"])
def identify_plant():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # Save filename and path
    filename = secure_filename(f"{uuid.uuid4()}_{file.filename}")
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    plant_scientific = "Unknown"
    plant_local = "Unknown"
    probability = 0.0

    # Identification Logic
    try:
        with open(filepath, 'rb') as img:
            files = {'images': (filename, img)}
            data = {'organs': ['auto']}
            response = requests.post(API_URL, files=files, data=data)

            if response.status_code == 200:
                results = response.json().get('results', [])
                if results:
                    result = results[0]
                    plant_scientific = result['species']['scientificNameWithoutAuthor']
                    commons = result['species'].get('commonNames', [])
                    if commons:
                        plant_local = commons[0]
                    probability = result['score']
    except Exception as e:
        print(f"Identification error: {e}")

    # Database Logic
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO plant_logs(image_filename, plant_name, local_name, probability)
        VALUES (%s, %s, %s, %s)
    """, (filename, plant_scientific, plant_local, probability))
    conn.commit()
    cur.close()
    conn.close()

    # --- CORRECTED RETURN PATH ---
    # Flask serves 'static_folder' content automatically. 
    # Since your static_folder is "assets", the URL is /assets/uploads/...
    return jsonify({
        "scientific": plant_scientific,
        "local": plant_local,
        "accuracy": round(probability * 100, 2),
        "image": f"/assets/uploads/{filename}" 
    })

from flask import redirect

@plant_bp.route("/plant/history/delete/<int:plant_id>", methods=["POST"])
def delete_history(plant_id):
    conn = get_db_connection()
    cur = conn.cursor()

    # Get image filename to delete from folder
    cur.execute(
        "SELECT image_filename FROM plant_logs WHERE id = %s",
        (plant_id,)
    )
    row = cur.fetchone()

    if row:
        image_filename = row[0]
        image_path = os.path.join(UPLOAD_FOLDER, image_filename)

        # Delete image file if exists
        if os.path.exists(image_path):
            os.remove(image_path)

        # Delete database record
        cur.execute(
            "DELETE FROM plant_logs WHERE id = %s",
            (plant_id,)
        )
        conn.commit()

    cur.close()
    conn.close()

    return redirect(url_for("plant_bp.plant_history"))
