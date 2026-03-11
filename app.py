from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key")

# Database SQLite
db_path = "/opt/render/project/src/applications.db"
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


class JobApplication(db.Model):
    __tablename__ = "job_applications"

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(50), nullable=False)

    what_you_want = db.Column(db.Text, nullable=True)
    role = db.Column(db.String(100), nullable=False)
    has_experience = db.Column(db.String(20), nullable=False)
    experience_summary = db.Column(db.Text, nullable=True)
    attitude = db.Column(db.Text, nullable=True)
    how_found = db.Column(db.String(100), nullable=True)
    how_found_other = db.Column(db.String(255), nullable=True)


@app.route("/", methods=["GET"])
@app.route("/join-our-team", methods=["GET"])
def candidatura_prestigio():
    return render_template("application_form.html")


@app.route("/join-our-team/apply", methods=["POST"])
def candidatura_prestigio_apply():
    data = request.get_json(silent=True)
    if not data:
        data = request.form.to_dict(flat=True)

    nome = (data.get("nome") or data.get("fullName") or "").strip()
    email = (data.get("email") or "").strip()
    telefono = (data.get("telefono") or data.get("phone") or "").strip()
    obiettivo = (data.get("obiettivo") or data.get("whatYouWant") or "").strip()
    ruolo = (data.get("ruolo") or data.get("role") or "").strip()
    esperienza = (data.get("esperienza") or data.get("hasExperience") or "").strip()
    descrizione_esperienza = (data.get("descrizione_esperienza") or data.get("experienceSummary") or "").strip()
    descrizione_personale = (data.get("descrizione_personale") or data.get("attitude") or "").strip()
    come_ci_ha_conosciuto = (data.get("come_ci_ha_conosciuto") or data.get("howFound") or "").strip()
    altro = (data.get("altro") or data.get("howFoundOther") or "").strip()

    if not nome or not email or not telefono or not ruolo or not esperienza:
        return jsonify({
            "success": False,
            "message": "Compila tutti i campi obbligatori."
        }), 400

    try:
        app_job = JobApplication(
            full_name=nome,
            email=email,
            phone=telefono,
            what_you_want=obiettivo or None,
            role=ruolo,
            has_experience=esperienza,
            experience_summary=descrizione_esperienza or None,
            attitude=descrizione_personale or None,
            how_found=come_ci_ha_conosciuto or None,
            how_found_other=altro or None,
        )

        db.session.add(app_job)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Candidatura inviata con successo."
        }), 200

    except Exception as e:
        db.session.rollback()
        app.logger.exception("Errore durante il salvataggio della candidatura")
        return jsonify({
            "success": False,
            "message": f"Errore server: {str(e)}"
        }), 500


@app.route("/admin", methods=["GET"])
@app.route("/join-our-team/elenco", methods=["GET"])
def candidatura_list():
    jobs = JobApplication.query.order_by(JobApplication.created_at.desc()).all()
    return render_template("admin.html", applications=jobs)


@app.route("/join-our-team/<int:application_id>", methods=["GET"])
def candidatura_detail(application_id):
    app_job = JobApplication.query.get_or_404(application_id)
    return jsonify({
        "id": app_job.id,
        "created_at": app_job.created_at.isoformat(),
        "full_name": app_job.full_name,
        "email": app_job.email,
        "phone": app_job.phone,
        "what_you_want": app_job.what_you_want,
        "role": app_job.role,
        "has_experience": app_job.has_experience,
        "experience_summary": app_job.experience_summary,
        "attitude": app_job.attitude,
        "how_found": app_job.how_found,
        "how_found_other": app_job.how_found_other,
    })


with app.app_context():
    db.create_all()


if __name__ == "__main__":
    app.run(debug=True)
