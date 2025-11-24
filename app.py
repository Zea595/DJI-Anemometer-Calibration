from flask import Flask, request, render_template, redirect, url_for, flash
import os
import import_cleaned_data
from scripts import convert_anemometer, Clean_and_Timestamp

UPLOAD_DIR = "/app/uploads"
DATA_DIR = "/data"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

app = Flask(__name__)
app.secret_key = "supersecret"


# =====================================================
# HOME PAGE
# =====================================================
@app.route("/")
def index():
    return render_template("upload.html")


# =====================================================
# FILE UPLOAD HANDLER
# =====================================================
@app.route("/upload", methods=["POST"])
def upload():
    drone_file = request.files.get("drone")
    anemo_file = request.files.get("anemo")
    

    if not (drone_file or anemo_file):
        flash("Please upload at least one file.")
        return redirect(url_for("index"))

    # ----------------------------
    # DRONE FILE PROCESSING
    # ----------------------------
    if drone_file:
        drone_path = os.path.join(UPLOAD_DIR, drone_file.filename)
        drone_file.save(drone_path)
        try:
            Clean_and_Timestamp.main(drone_path)
            flash(f"✅ Processed drone data: {drone_file.filename}")
        except Exception as e:
            flash(f"❌ Error processing drone file: {e}")
            return redirect(url_for("index"))

    # ----------------------------
    # ANEMOMETER FILE PROCESSING
    # ----------------------------
    if anemo_file:
        anemo_path = os.path.join(UPLOAD_DIR, anemo_file.filename)
        anemo_file.save(anemo_path)
        try:
            out_path = convert_anemometer.convert_file(anemo_path, None, "America/Vancouver")
            flash(f"✅ Converted anemometer log to {os.path.basename(out_path)}")
        except Exception as e:
            flash(f"❌ Error converting anemometer log: {e}")
            return redirect(url_for("index"))

    # ----------------------------
    # DATABASE INGESTION
    # ----------------------------
    try:
        import_cleaned_data.ingest_drone()
        import_cleaned_data.ingest_anemometer()
        flash("✅ Data successfully imported into PostgreSQL.")
    except Exception as e:
        flash(f"⚠️ Data import warning: {e}")

    return redirect(url_for("index"))


# =====================================================
# ANALYTICS PAGE
# =====================================================
@app.route("/analytics")
def analytics():
    try:
        from scripts import compare
        used_file = compare.generate_plots()
        flash(f"📊 Analytics generated successfully from {os.path.basename(used_file)}")
        return render_template("analytics.html")
    except Exception as e:
        flash(f"Error generating analytics: {e}")
        return redirect(url_for("index"))


# =====================================================
# APP ENTRYPOINT
# =====================================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
