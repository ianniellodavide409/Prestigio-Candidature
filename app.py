from flask import (
    Flask, render_template, request, jsonify, Response,
    redirect, url_for, session, render_template_string
)
from datetime import datetime, timedelta
import os
import csv
import io
import json
import re
import gspread
from functools import wraps
from google.oauth2.service_account import Credentials

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or os.environ.get("FLASK_SECRET_KEY") or "dev-secret-key"

SPREADSHEET_ID = "1D99OBEH-0s186n279kghjZEcK43a6RtC5MVfKnT-cMs"
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "").strip()

# anti-spam leggero in memoria
LAST_SUBMISSIONS = {}

EMAIL_REGEX = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
PHONE_REGEX = re.compile(r"^[\d\s\+\-\(\)]{6,20}$")


def get_sheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]

    creds_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")

    if creds_json:
        creds_dict = json.loads(creds_json)
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    else:
        credentials = Credentials.from_service_account_file(
            "prestigio-candidature-d1aeb5c4206b.json",
            scopes=scopes
        )

    client = gspread.authorize(credentials)
    return client.open_by_key(SPREADSHEET_ID).sheet1


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("admin_logged_in"):
            if request.path.startswith("/admin/api/"):
                return jsonify({"success": False, "message": "Non autorizzato."}), 401
            return redirect(url_for("admin_login"))
        return fn(*args, **kwargs)
    return wrapper


def normalize_bool(value):
    return str(value).strip().lower() == "true"


def get_client_ip():
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr or "unknown"


def validate_text_length(value, max_len=500):
    return len((value or "").strip()) <= max_len


@app.route("/", methods=["GET"])
@app.route("/join-our-team", methods=["GET"])
def candidatura_prestigio():
    return render_template("application_form.html")


@app.route("/join-our-team/apply", methods=["POST"])
def candidatura_prestigio_apply():
    try:
        data = request.get_json(silent=True)
        if not data:
            data = request.form.to_dict(flat=True)

        nome = (data.get("nome") or "").strip()
        email = (data.get("email") or "").strip()
        telefono = (data.get("telefono") or "").strip()
        obiettivo = (data.get("obiettivo") or "").strip()
        ruolo = (data.get("ruolo") or "").strip()
        esperienza = (data.get("esperienza") or "").strip()
        descrizione_esperienza = (data.get("descrizione_esperienza") or "").strip()
        descrizione_personale = (data.get("descrizione_personale") or "").strip()
        come_ci_ha_conosciuto = (data.get("come_ci_ha_conosciuto") or "").strip()
        altro = (data.get("altro") or "").strip()

        app.logger.info("Richiesta candidatura ricevuta")

        if not nome or not email or not telefono or not ruolo or not esperienza:
            app.logger.warning("Campi obbligatori mancanti")
            return jsonify({
                "success": False,
                "message": "Compila tutti i campi obbligatori."
            }), 400

        sheet = get_sheet()
        now_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        app.logger.info("Inizio append su Google Sheets")

        sheet.append_row([
            now_str,
            nome,
            email,
            telefono,
            obiettivo,
            ruolo,
            esperienza,
            descrizione_esperienza,
            descrizione_personale,
            come_ci_ha_conosciuto,
            altro,
            "False"
        ])

        app.logger.info("Append completato su Google Sheets")

        return jsonify({
            "success": True,
            "message": "Candidatura inviata con successo."
        }), 200

    except Exception as e:
        app.logger.exception("Errore durante il salvataggio candidatura")
        return jsonify({
            "success": False,
            "message": f"Errore server: {str(e)}"
        }), 500
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    error = ""

    if request.method == "POST":
        password = (request.form.get("password") or "").strip()

        if ADMIN_PASSWORD and password == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            return redirect(url_for("candidatura_list"))
        error = "Password non corretta."

    return render_template_string("""
    <!DOCTYPE html>
    <html lang="it">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>Login Admin — Prestigio</title>
      <style>
        body{
          margin:0;background:#0d0d0d;color:#fff;font-family:Arial,sans-serif;
          display:flex;align-items:center;justify-content:center;min-height:100vh;
        }
        .box{
          background:#151515;border:1px solid rgba(196,149,42,.25);
          padding:32px;width:100%;max-width:380px;border-radius:6px;
        }
        h1{margin:0 0 18px;font-size:22px}
        input{
          width:100%;padding:12px;border:1px solid #444;background:#fff;
          color:#111;border-radius:4px;margin-bottom:12px;box-sizing:border-box;
        }
        button{
          width:100%;padding:12px;background:#c4952a;color:#111;border:none;
          border-radius:4px;font-weight:700;cursor:pointer;
        }
        .err{color:#ffb3b3;margin-bottom:12px;font-size:14px}
      </style>
    </head>
    <body>
      <div class="box">
        <h1>Accesso Admin</h1>
        {% if error %}<div class="err">{{ error }}</div>{% endif %}
        <form method="POST">
          <input type="password" name="password" placeholder="Password admin" required>
          <button type="submit">Entra</button>
        </form>
      </div>
    </body>
    </html>
    """, error=error)


@app.route("/admin", methods=["GET"])
@app.route("/join-our-team/elenco", methods=["GET"])
@admin_required
def candidatura_list():
    return render_template("admin.html")


@app.route("/admin/api/applications", methods=["GET"])
@admin_required
def admin_api_applications():
    try:
        sheet = get_sheet()
        rows = sheet.get_all_records()

        results = []
        total_rows = len(rows)

        for idx, row in enumerate(reversed(rows), start=1):
            real_sheet_row = total_rows - idx + 2  # +2 perchè riga 1 è header

            results.append({
                "id": real_sheet_row,
                "created_at": row.get("created_at", ""),
                "nome": row.get("full_name", ""),
                "email": row.get("email", ""),
                "telefono": row.get("phone", ""),
                "obiettivo": row.get("what_you_want", ""),
                "ruolo": row.get("role", ""),
                "esperienza": row.get("has_experience", ""),
                "descrizione_esperienza": row.get("experience_summary", ""),
                "descrizione_personale": row.get("attitude", ""),
                "come_ci_ha_conosciuto": row.get("how_found", ""),
                "altro": row.get("how_found_other", ""),
                "interessante": normalize_bool(row.get("interesting", "False")),
            })

        return jsonify(results), 200

    except Exception as e:
        app.logger.exception("Errore lettura candidature da Google Sheets")
        return jsonify({
            "success": False,
            "message": "Errore lettura candidature."
        }), 500


@app.route("/admin/api/export", methods=["GET"])
@admin_required
def admin_api_export():
    try:
        sheet = get_sheet()
        rows = sheet.get_all_records()

        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow([
            "Data creazione",
            "Nome completo",
            "Email",
            "Telefono",
            "Obiettivo",
            "Ruolo",
            "Esperienza",
            "Descrizione esperienza",
            "Descrizione personale",
            "Come ci ha conosciuto",
            "Altro",
            "Interessante",
        ])

        for row in rows:
            writer.writerow([
                row.get("created_at", ""),
                row.get("full_name", ""),
                row.get("email", ""),
                row.get("phone", ""),
                row.get("what_you_want", ""),
                row.get("role", ""),
                row.get("has_experience", ""),
                row.get("experience_summary", ""),
                row.get("attitude", ""),
                row.get("how_found", ""),
                row.get("how_found_other", ""),
                row.get("interesting", ""),
            ])

        csv_data = output.getvalue()
        output.close()

        return Response(
            csv_data,
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=candidature_prestigio.csv"}
        )

    except Exception as e:
        app.logger.exception("Errore export CSV")
        return Response("Errore durante l'export.", status=500)


@app.route("/admin/api/toggle/<int:application_id>", methods=["POST"])
@admin_required
def admin_api_toggle(application_id):
    try:
        if application_id < 2:
            return jsonify({"success": False, "message": "ID non valido."}), 400

        sheet = get_sheet()
        current_value = sheet.cell(application_id, 12).value
        new_value = "False" if normalize_bool(current_value) else "True"
        sheet.update_cell(application_id, 12, new_value)

        return jsonify({
            "success": True,
            "interessante": normalize_bool(new_value)
        }), 200

    except Exception:
        app.logger.exception("Errore toggle candidatura")
        return jsonify({
            "success": False,
            "message": "Errore durante l'aggiornamento."
        }), 500


@app.route("/admin/api/delete/<int:application_id>", methods=["DELETE"])
@admin_required
def admin_api_delete(application_id):
    try:
        if application_id < 2:
            return jsonify({"success": False, "message": "ID non valido."}), 400

        sheet = get_sheet()
        sheet.delete_rows(application_id)

        return jsonify({
            "success": True,
            "message": "Candidatura eliminata."
        }), 200

    except Exception:
        app.logger.exception("Errore delete candidatura")
        return jsonify({
            "success": False,
            "message": "Errore durante l'eliminazione."
        }), 500


@app.route("/admin/logout", methods=["GET"])
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"success": True, "status": "ok"}), 200


if __name__ == "__main__":
    app.run(debug=True)
