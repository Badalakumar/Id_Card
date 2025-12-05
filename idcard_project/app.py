from flask import Flask, render_template, request, session, jsonify, send_file, redirect, url_for
import os, io, zipfile
from PIL import Image, ImageDraw, ImageFont

app = Flask(__name__)
app.secret_key = "id_card_secret"

# Folder paths
UPLOAD_FOLDER = "static/uploads"
OUTPUT_FOLDER = "static/output"
TEMPLATE = "static/template/base.png"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

BASE_WIDTH = 600
BASE_HEIGHT = 300

# Default layout (if user hasn't moved anything)
DEFAULT_LAYOUT = {
    "profile": {"top": 20, "left": 20},
    "name": {"top": 20, "left": 170},
    "email": {"top": 60, "left": 170},
    "phone": {"top": 100, "left": 170},
    "id": {"top": 140, "left": 170},
    "dept": {"top": 180, "left": 170},
}

@app.route("/")
def index():
    return render_template("input.html")


# -----------------------------
#  ADD USER & STORE IN SESSION
# -----------------------------
@app.route("/add_user", methods=["POST"])
def add_user():
    name = request.form.get("name", "")
    email = request.form.get("email", "")
    phone = request.form.get("phone", "")
    uid = request.form.get("uid", "")
    dept = request.form.get("dept", "")

    bg = request.files.get("background")
    profile = request.files.get("profile")

    bg_path = ""
    profile_path = ""

    # Save background
    if bg and bg.filename:
        filename = bg.filename
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        bg.save(filepath)
        bg_path = "/" + filepath.replace("\\", "/")

    # Save Profile
    if profile and profile.filename:
        filename = profile.filename
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        profile.save(filepath)
        profile_path = "/" + filepath.replace("\\", "/")

    # User Data Structure
    user = {
        "name": name,
        "email": email,
        "phone": phone,
        "id": uid,
        "dept": dept,
        "background": bg_path,
        "profile": profile_path
    }

    users = session.get("ALL_USERS", [])
    users.append(user)
    session["ALL_USERS"] = users

    return redirect(url_for("editor", index=len(users)-1))


# -----------------------------
#        EDITOR PAGE
# -----------------------------
@app.route("/editor")
def editor():
    idx = int(request.args.get("index", 0))
    users = session.get("ALL_USERS", [])

    if idx < 0 or idx >= len(users):
        return "Invalid user index", 400

    user = users[idx]
    layout = session.get("MASTER_LAYOUT", DEFAULT_LAYOUT)

    return render_template("editor.html", user=user, layout=layout, index=idx)


# -----------------------------
#         SAVE LAYOUT
# -----------------------------
@app.route("/save_layout", methods=["POST"])
def save_layout():
    layout = request.json
    session["MASTER_LAYOUT"] = layout
    return jsonify({"status": "saved"})


# -----------------------------
#      GENERATE IMAGE FILE
# -----------------------------
def generate_card_image(user, layout):

    # Load background
    if user["background"] and os.path.exists(user["background"][1:]):
        base = Image.open(user["background"][1:]).convert("RGBA")
    else:
        base = Image.open(TEMPLATE).convert("RGBA")

    base = base.resize((BASE_WIDTH, BASE_HEIGHT))
    draw = ImageDraw.Draw(base)

    # Font
    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except:
        font = ImageFont.load_default()

    # Profile image
    if user["profile"] and os.path.exists(user["profile"][1:]):
        prof = Image.open(user["profile"][1:]).convert("RGBA")
        prof = prof.resize((120, 120))
        base.paste(prof, (layout["profile"]["left"], layout["profile"]["top"]), prof)

    # Text
    draw.text((layout["name"]["left"], layout["name"]["top"]), user["name"], fill="black", font=font)
    draw.text((layout["email"]["left"], layout["email"]["top"]), user["email"], fill="black", font=font)
    draw.text((layout["phone"]["left"], layout["phone"]["top"]), user["phone"], fill="black", font=font)
    draw.text((layout["id"]["left"], layout["id"]["top"]), user["id"], fill="black", font=font)
    draw.text((layout["dept"]["left"], layout["dept"]["top"]), user["dept"], fill="black", font=font)

    # Save output
    outname = f"{user['id']}.png"
    output_path = os.path.join(OUTPUT_FOLDER, outname)
    base.convert("RGB").save(output_path)

    return output_path


# -----------------------------
#      DOWNLOAD ALL CARDS
# -----------------------------
@app.route("/download_all")
def download_all():
    users = session.get("ALL_USERS", [])
    layout = session.get("MASTER_LAYOUT", DEFAULT_LAYOUT)

    if not users:
        return "No users to generate!"

    buf = io.BytesIO()

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for u in users:
            path = generate_card_image(u, layout)
            z.write(path, os.path.basename(path))

    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name="All_ID_Cards.zip")


@app.route("/download_single")
def download_single():
    idx = int(request.args.get("index", 0))
    
    users = session.get("ALL_USERS", [])
    layout = session.get("MASTER_LAYOUT", DEFAULT_LAYOUT)

    if idx < 0 or idx >= len(users):
        return "Invalid index"

    user = users[idx]
    img_path = generate_card_image(user, layout)

    return send_file(img_path, as_attachment=True)



# -----------------------------
#      USERS LIST PAGE
# -----------------------------
@app.route("/users")
def users_list():
    return render_template("users.html", users=session.get("ALL_USERS", []))


if __name__ == "__main__":
    app.run(debug=True)
