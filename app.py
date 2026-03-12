from flask import Flask, render_template, request, jsonify, Response, redirect, url_for
from datetime import datetime
import os
import csv
import io
import json
import gspread
from google.oauth2.service_account import Credentials

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key")

SHEET_NAME = "Prestigio Candidature"

# --- Google Sheets setup ---
def get_sheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    # 1) Preferisce credenziali da variabile ambiente (Render)
    creds_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")

    if creds_json:
        creds_dict = json.loads(creds_json)
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    else:
        # 2) Fallback locale: file JSON sul computer/server
        credentials = Credentials.from_service_account_file(
            "prestigio-candidature-d1aeb5c4206b.json",
            scopes=scopes
        )

    client = gspread.authorize(credentials)
    return client.open(SHEET_NAME).sheet1


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
        sheet = get_sheet()
        now_str = datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S")

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

        return jsonify({
            "success": True,
            "message": "Candidatura inviata con successo."
        }), 200

    except Exception as e:
        app.logger.exception("Errore durante il salvataggio della candidatura su Google Sheets")
        return jsonify({
            "success": False,
            "message": f"Errore server: {str(e)}"
        }), 500


@app.route("/admin", methods=["GET"])
@app.route("/join-our-team/elenco", methods=["GET"])
def candidatura_list():
    return render_template("admin.html")


@app.route("/admin/api/applications", methods=["GET"])
def admin_api_applications():
    try:
        sheet = get_sheet()
        rows = sheet.get_all_records()

        results = []
        # ultima riga in alto
        for idx, row in enumerate(reversed(rows), start=1):
            results.append({
                "id": len(rows) - idx + 2,  # indice riga sheet approssimato
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
                "interessante": str(row.get("interesting", "False")).lower() == "true",
            })

        return jsonify(results), 200

    except Exception as e:
        app.logger.exception("Errore lettura candidature da Google Sheets")
        return jsonify([]), 200


@app.route("/admin/api/export", methods=["GET"])
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
        return Response("Errore durante l'export", status=500)


@app.route("/admin/api/toggle/<int:application_id>", methods=["POST"])
def admin_api_toggle(application_id):
    return jsonify({
        "success": False,
        "message": "Funzione toggle non ancora attiva con Google Sheets."
    }), 501


@app.route("/admin/api/delete/<int:application_id>", methods=["DELETE"])
def admin_api_delete(application_id):
    return jsonify({
        "success": False,
        "message": "Funzione delete non ancora attiva con Google Sheets."
    }), 501


@app.route("/admin/logout", methods=["GET"])
def admin_logout():
    return redirect(url_for("candidatura_prestigio"))


if __name__ == "__main__":
    app.run(debug=True)
