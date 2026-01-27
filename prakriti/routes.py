from flask import render_template, request, session, redirect, url_for

from . import prakriti_bp

HERBS = {
    "Vata": ["Ashwagandha", "Shatavari", "Licorice", "Brahmi"],
    "Pitta": ["Amla", "Neem", "Guduchi", "Aloe Vera"],
    "Kapha": ["Tulsi", "Ginger", "Trikatu", "Punarnava"],
    "Vata-Pitta": ["Ashwagandha", "Shatavari", "Amla", "Brahmi"],
    "Pitta-Kapha": ["Neem", "Guduchi", "Tulsi", "Aloe Vera"],
    "Vata-Kapha": ["Ginger", "Trikatu", "Ashwagandha", "Punarnava"],
    "Tridoshaja": ["Triphala", "Guduchi", "Tulsi", "Amalaki"]
}

@prakriti_bp.route("/form")
def prakriti_form():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("prakriti_form.html")


@prakriti_bp.route("/result", methods=["POST"])
def prakriti_result():
    vata = pitta = kapha = 0

    for _, value in request.form.items():
        if value == "vata": vata += 1
        elif value == "pitta": pitta += 1
        elif value == "kapha": kapha += 1

    scores = {"Vata": vata, "Pitta": pitta, "Kapha": kapha}
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    if sorted_scores[0][1] == sorted_scores[1][1] == sorted_scores[2][1]:
        prakriti = "Tridoshaja"
    elif sorted_scores[0][1] == sorted_scores[1][1]:
        prakriti = f"{sorted_scores[0][0]}-{sorted_scores[1][0]}"
    else:
        prakriti = sorted_scores[0][0]

    herbs = HERBS.get(prakriti, [])

    return render_template(
        "result.html",
        prakriti=prakriti,
        vata=vata,
        pitta=pitta,
        kapha=kapha,
        herbs=herbs
    )
