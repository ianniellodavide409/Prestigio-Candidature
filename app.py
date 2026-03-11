from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os


app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///applications.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Personal information
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    date_of_birth = db.Column(db.String(20), nullable=False)
    birth_place = db.Column(db.String(150), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(150), nullable=False)

    # Education
    highest_degree = db.Column(db.String(255), nullable=False)
    institution = db.Column(db.String(255), nullable=False)
    training = db.Column(db.Text, nullable=True)

    # Skills
    technical_skills = db.Column(db.Text, nullable=True)  # comma-separated
    technical_skills_other = db.Column(db.Text, nullable=True)
    soft_skills = db.Column(db.Text, nullable=True)       # comma-separated
    soft_skills_other = db.Column(db.Text, nullable=True)

# Experience & motivation
    experience_jewelry = db.Column(db.Text, nullable=False)
    motivation = db.Column(db.Text, nullable=False)


class JobApplication(db.Model):
    """Candidature per Sales Assistant e E-commerce Support (Prestigio)."""
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(50), nullable=False)
    what_you_want = db.Column(db.Text, nullable=True)
    role = db.Column(db.String(100), nullable=False)  # Sales Assistant | E-commerce Support
    has_experience = db.Column(db.String(10), nullable=False)  # sì | no
    experience_summary = db.Column(db.Text, nullable=True)
    attitude = db.Column(db.Text, nullable=True)  # domanda personale sull'attitudine
    how_found = db.Column(db.String(100), nullable=True)
    how_found_other = db.Column(db.String(255), nullable=True)


def create_tables():
    """Create database tables if they don't exist."""
    with app.app_context():
        db.create_all()


@app.route("/", methods=["GET"])
def index():
    return render_template("application_form.html")


@app.route("/applications", methods=["GET"])
def list_applications():
    applications = Application.query.order_by(Application.created_at.desc()).all()
    return render_template("applications_list.html", applications=applications)


@app.route("/applications/<int:application_id>", methods=["GET"])
def application_detail(application_id):
    application = Application.query.get_or_404(application_id)
    return render_template("application_detail.html", application=application)


# --- Prestigio: candidature Sales Assistant / E-commerce Support ---
@app.route("/join-our-team", methods=["GET"])
def candidatura_prestigio():
    return render_template("candidatura_prestigio.html")


@app.route("/join-our-team/apply", methods=["POST"])
def candidatura_prestigio_apply():
    data = request.get_json(silent=True) or {}

    nome = (data.get("nome") or "").strip()
    email = (data.get("email") or "").strip()
    telefono = (data.get("telefono") or "").strip()
    ruolo = (data.get("ruolo") or "").strip()
    esperienza = (data.get("esperienza") or "").strip()
    descrizione_esperienza = (data.get("descrizione_esperienza") or "").strip()
    descrizione_personale = (data.get("descrizione_personale") or "").strip()
    come_ci_ha_conosciuto = (data.get("come_ci_ha_conosciuto") or "").strip()
    altro = (data.get("altro") or "").strip()
    obiettivo = (data.get("obiettivo") or "").strip()

    if not nome or not email or not telefono or not ruolo or not esperienza:
        return {"success": False, "message": "Compila tutti i campi obbligatori."}, 400

    parts = nome.split()
    first_name = parts[0] if parts else ""
    last_name = " ".join(parts[1:]) if len(parts) > 1 else ""

    application = Application(
        first_name=first_name or nome,
        last_name=last_name or "-",
        date_of_birth="-",
        birth_place="-",
        address="-",
        phone=telefono,
        email=email,
        highest_degree="-",
        institution="-",
        field_of_study=None,
        graduation_year=None,
        training=None,
        technical_skills=None,
        technical_skills_other=None,
        soft_skills=None,
        soft_skills_other=None,
        experience_jewelry=descrizione_esperienza or esperienza,
        motivation=descrizione_personale or obiettivo or f"Ruolo: {ruolo}; Come ci ha conosciuto: {come_ci_ha_conosciuto}; Altro: {altro}"
    )

    db.session.add(application)
    db.session.commit()

    return {"success": True, "message": "Candidatura inviata con successo."}, 200

    app_job = JobApplication(
        full_name=request.form.get("fullName", "").strip(),
        email=request.form.get("email", "").strip(),
        phone=request.form.get("phone", "").strip(),
        what_you_want=(request.form.get("whatYouWant") or "").strip() or None,
        role=request.form.get("role", "").strip(),
        has_experience=request.form.get("hasExperience", "").strip(),
        experience_summary=(request.form.get("experienceSummary") or "").strip() or None,
        attitude=(request.form.get("attitude") or "").strip() or None,
        how_found=request.form.get("howFound") or None,
        how_found_other=(request.form.get("howFoundOther") or "").strip() or None,
    )
    db.session.add(app_job)
    db.session.commit()

    flash("La tua candidatura è stata inviata. Ti contatteremo al più presto.", "success")
    return redirect(url_for("candidatura_prestigio"))


@app.route("/join-our-team/elenco", methods=["GET"])
def candidatura_list():
    jobs = JobApplication.query.order_by(JobApplication.created_at.desc()).all()
    return render_template("candidatura_list.html", applications=jobs)


@app.route("/join-our-team/<int:application_id>", methods=["GET"])
def candidatura_detail(application_id):
    app_job = JobApplication.query.get_or_404(application_id)
    return render_template("candidatura_detail.html", application=app_job)


@app.route("/apply", methods=["POST"])
def apply():
    required_fields = [
        "firstName", "lastName", "dob", "birthPlace", "address",
        "phone", "email", "highestDegree", "institution",
        "experienceJewelry", "motivation",
    ]

    missing = [f for f in required_fields if not request.form.get(f)]
    if missing:
        flash("Please complete all required fields.", "error")
        return redirect(url_for("index"))

    technical_skills_list = request.form.getlist("technicalSkills")
    soft_skills_list = request.form.getlist("softSkills")

    application = Application(
        # Personal
        first_name=request.form.get("firstName", "").strip(),
        last_name=request.form.get("lastName", "").strip(),
        date_of_birth=request.form.get("dob"),
        birth_place=request.form.get("birthPlace", "").strip(),
        address=request.form.get("address", "").strip(),
        phone=request.form.get("phone", "").strip(),
        email=request.form.get("email", "").strip(),

        # Education
        highest_degree=request.form.get("highestDegree", "").strip(),
        institution=request.form.get("institution", "").strip(),
        training=(request.form.get("training") or None),

        # Skills
        technical_skills=",".join(technical_skills_list) if technical_skills_list else None,
        technical_skills_other=(request.form.get("technicalSkillsOther") or "").strip() or None,
        soft_skills=",".join(soft_skills_list) if soft_skills_list else None,
        soft_skills_other=(request.form.get("softSkillsOther") or "").strip() or None,

        # Experience & motivation
        experience_jewelry=request.form.get("experienceJewelry", "").strip(),
        motivation=request.form.get("motivation", "").strip(),
    )

    db.session.add(application)
    db.session.commit()

    flash("Thank you. Your application has been received.", "success")
    return redirect(url_for("index"))

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)

