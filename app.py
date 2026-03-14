from flask import Flask, request, jsonify, render_template, Response
import json
import os
from dotenv import load_dotenv
from groq import Groq
import re
from flask_cors import CORS
from conversation_controller import ConversationManager

load_dotenv()

app = Flask(__name__)
CORS(app)

convman = ConversationManager()

# ──────────────────────────────────────────────
# Groq Client
# ──────────────────────────────────────────────

def get_groq_client() -> Groq:
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        raise RuntimeError("GROQ_API_KEY not set in .env")
    return Groq(api_key=key)


# ──────────────────────────────────────────────
# Groq-powered field extractor (replaces all regex parsers)
# ──────────────────────────────────────────────

# Field-specific JSON schemas and instructions for the LLM
FIELD_PROMPTS = {
    "name": {
        "schema": '{"name": "<First Last>"}',
        "instruction": (
            "Extract the person's full name from the spoken text. "
            "Return only the name in title case, max 3 words. "
            "Remove phrases like 'my name is', 'I am', 'this is'. "
        ),
    },
    "contact": {
        "schema": '{"email": "example@domain.com", "phone": "+91XXXXXXXXXX"}',
        "instruction": (
            "Extract the email and phone number from the spoken text. "
            "The user may say 'dot' instead of '.', 'at' instead of '@', 'underscore' instead of '_'. "
            "Convert spoken email like 'john dot doe at gmail dot com' to 'john.doe@gmail.com'. "
            "The phone should contain only digits and an optional leading '+'. "
            "If email or phone is not found, return an empty string for that field. "
        ),
    },
    "education": {
        "schema": '{"institution": "<university name>", "degree": "<B.Tech/M.Sc/etc>", "field": "<subject>", "cgpa": "<number>", "year": "<graduation year>"}',
        "instruction": (
            "Extract education details from the spoken text. "
            "Identify the institution name, degree type (B.Tech, M.Tech, B.Sc, M.Sc, BCA, MCA, MBA, Diploma, etc.), "
            "field of study, CGPA/GPA, and graduation year. "
            "Leave any missing fields as empty string. "
        ),
    },
    "skills": {
        "schema": '{"skills": ["Skill One", "Skill Two", "Skill Three"]}',
        "instruction": (
            "Extract individual technical and professional skills from the spoken text. "
            "Return each as a separate item in the list. Title case each skill. "
            "Common separators: 'and', commas, '/', '+'. "
            "Do not include filler words like 'my skills are', 'I know'. "
        ),
    },
    "experience": {
        "schema": '{"company": "<Company Name>", "role": "<Job Title>", "startYear": "<YYYY>", "endYear": "<YYYY or present>"}',
        "instruction": (
            "Extract work experience details from the spoken text. "
            "Identify: company/organisation name, job title/role, start year, end year (or 'present'). "
            "Look for patterns like 'worked as X at Y from 2021 to 2024'. "
            "Leave missing fields as empty string. "
        ),
    },
    "projects": {
        "schema": '{"title": "<project name>", "description": "<what it does>", "tech": "<technologies used>"}',
        "instruction": (
            "Extract project details from the spoken text. "
            "Identify the project title, a short description of what it does, and the technologies/tools used. "
            "Leave missing fields as empty string. "
        ),
    },
    "certifications": {
        "schema": '{"certifications": ["Cert One", "Cert Two"]}',
        "instruction": (
            "Extract certifications, courses, or credentials from the spoken text. "
            "Return each as a separate item. "
            "Examples: 'AWS Certified Developer', 'Google Data Analytics', 'Coursera Machine Learning'. "
        ),
    },
    "linkedin": {
        "schema": '{"url": "https://linkedin.com/in/username"}',
        "instruction": (
            "Extract or construct the LinkedIn profile URL from the spoken text. "
            "The user may say 'dot' for '.', 'slash' for '/'. "
            "Convert to a proper https:// URL. "
            "If just a username is given, format as https://linkedin.com/in/username. "
        ),
    },
    "github": {
        "schema": '{"url": "https://github.com/username"}',
        "instruction": (
            "Extract or construct the GitHub or portfolio URL from the spoken text. "
            "The user may say 'dot' for '.', 'slash' for '/'. "
            "Convert to a proper https:// URL. "
            "If just a username is given, format as https://github.com/username. "
        ),
    },
}

GENERIC_PROMPT = {
    "schema": '{"value": "<extracted text>"}',
    "instruction": "Clean up and return the most meaningful text from the user's spoken input.",
}


def parse_with_groq(field: str, text: str) -> dict:
    """
    Use Groq LLM to extract structured JSON for a given resume field.
    Returns a dict with the parsed data, or None on failure.
    """
    if not text or not text.strip():
        return None

    try:
        client = get_groq_client()
        field_lower = (field or "").lower()
        meta = FIELD_PROMPTS.get(field_lower, GENERIC_PROMPT)

        system_prompt = (
            "You are a precise JSON extractor for a voice-powered resume builder. "
            "The user speaks their answers, sometimes using spoken conventions like "
            "'dot' for '.', 'at' for '@', 'slash' for '/', 'underscore' for '_'. "
            "Your job: extract the information and return ONLY a valid JSON object "
            f"in exactly this shape: {meta['schema']}. "
            "Do not include any explanation, markdown, or extra text. "
            "Only output the JSON object."
        )

        user_prompt = (
            f"Field to extract: {field_lower}\n"
            f"Instruction: {meta['instruction']}\n\n"
            f"User's spoken input: \"{text}\"\n\n"
            f"Return JSON matching the schema: {meta['schema']}"
        )

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            temperature=0,
            max_tokens=300,
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content.strip()
        parsed = json.loads(raw)
        print(f"[GROQ] field={field_lower} → {parsed}")
        return parsed

    except Exception as e:
        print(f"[GROQ ERROR] field={field}, error={type(e).__name__}: {e}")
        return None


# ──────────────────────────────────────────────
# HTML escape helper
# ──────────────────────────────────────────────

def _esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

def _skills_html(skills):
    return "".join(f"<span class='skill-badge'>{_esc(s)}</span>" for s in skills)


# ──────────────────────────────────────────────
# Resume Template Renderers (unchanged)
# ──────────────────────────────────────────────

def render_modern(d):
    name  = _esc(d.get("name", "Your Name"))
    role  = _esc(d.get("job_role", "Professional"))
    email = _esc(d.get("email", ""))
    phone = _esc(d.get("phone", ""))
    linkedin = _esc(d.get("linkedin", ""))
    github   = _esc(d.get("github", ""))
    summary  = _esc(d.get("summary", ""))
    skills   = d.get("skills", [])
    experience     = d.get("experience", [])
    education      = d.get("education", [])
    projects       = d.get("projects", [])
    certifications = d.get("certifications", [])
    additional     = _esc(d.get("additional", ""))

    contact_parts = []
    if email:    contact_parts.append(f"<span>✉ {email}</span>")
    if phone:    contact_parts.append(f"<span>📞 {phone}</span>")
    if linkedin: contact_parts.append(f"<span>🔗 {linkedin}</span>")
    if github:   contact_parts.append(f"<span>💻 {github}</span>")

    exp_html  = "".join(f"<div class='entry'><p>{_esc(ex.get('text', ''))}</p></div>" for ex in experience)
    edu_html  = "".join(f"<div class='entry'><p>{_esc(ed.get('text', ''))}</p></div>" for ed in education)
    proj_html = "".join(f"<div class='entry'><p>{_esc(pr.get('text', ''))}</p></div>" for pr in projects)
    cert_list = "".join(f"<li>{_esc(c)}</li>" for c in certifications)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{name} – Resume</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
  *{{margin:0;padding:0;box-sizing:border-box;}}
  body{{font-family:'Inter',sans-serif;color:#1a1a2e;background:#fff;}}
  .resume{{max-width:800px;margin:0 auto;}}
  .header{{background:linear-gradient(135deg,#0066cc,#004499);color:#fff;padding:32px 40px;}}
  .header .name{{font-size:28px;font-weight:700;letter-spacing:0.5px;}}
  .header .role{{font-size:14px;opacity:.85;margin-top:4px;}}
  .header .contact{{display:flex;gap:18px;flex-wrap:wrap;margin-top:12px;font-size:12px;opacity:.9;}}
  .body{{padding:24px 40px;}}
  .section{{margin-bottom:20px;}}
  .sec-title{{font-size:11px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#0066cc;border-bottom:2px solid #0066cc;padding-bottom:4px;margin-bottom:10px;}}
  .summary{{font-size:13px;line-height:1.7;color:#444;}}
  .skills-wrap{{display:flex;flex-wrap:wrap;gap:6px;}}
  .skill-badge{{background:#e8f0ff;color:#0066cc;border:1px solid #c0d4ff;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:600;}}
  .entry{{margin-bottom:10px;}}
  .entry p{{font-size:12px;line-height:1.6;color:#333;}}
  .cert-list{{list-style:none;padding:0;}}
  .cert-list li{{font-size:12px;padding:2px 0;color:#333;}}
  .cert-list li::before{{content:"✓ ";color:#0066cc;font-weight:700;}}
  .additional{{font-size:12px;color:#444;line-height:1.6;}}
  @media print{{body{{-webkit-print-color-adjust:exact;print-color-adjust:exact;}}}}
</style>
</head>
<body>
<div class="resume">
  <div class="header">
    <div class="name">{name}</div>
    <div class="role">{role}</div>
    <div class="contact">{"".join(contact_parts)}</div>
  </div>
  <div class="body">
    {"<div class='section'><div class='sec-title'>Professional Summary</div><p class='summary'>" + summary + "</p></div>" if summary else ""}
    {"<div class='section'><div class='sec-title'>Skills</div><div class='skills-wrap'>" + _skills_html(skills) + "</div></div>" if skills else ""}
    {"<div class='section'><div class='sec-title'>Work Experience</div>" + exp_html + "</div>" if exp_html else ""}
    {"<div class='section'><div class='sec-title'>Education</div>" + edu_html + "</div>" if edu_html else ""}
    {"<div class='section'><div class='sec-title'>Projects</div>" + proj_html + "</div>" if proj_html else ""}
    {"<div class='section'><div class='sec-title'>Certifications</div><ul class='cert-list'>" + cert_list + "</ul></div>" if certifications else ""}
    {"<div class='section'><div class='sec-title'>Additional Information</div><p class='additional'>" + additional + "</p></div>" if additional else ""}
  </div>
</div>
</body>
</html>"""


def render_classic(d):
    name  = _esc(d.get("name", "Your Name"))
    role  = _esc(d.get("job_role", "Professional"))
    email = _esc(d.get("email", ""))
    phone = _esc(d.get("phone", ""))
    linkedin = _esc(d.get("linkedin", ""))
    github   = _esc(d.get("github", ""))
    summary  = _esc(d.get("summary", ""))
    skills   = d.get("skills", [])
    experience     = d.get("experience", [])
    education      = d.get("education", [])
    projects       = d.get("projects", [])
    certifications = d.get("certifications", [])
    additional     = _esc(d.get("additional", ""))

    contact_parts = [x for x in [email, phone, linkedin, github] if x]
    exp_html  = "".join(f"<p class='entry-text'>{_esc(ex.get('text',''))}</p>" for ex in experience)
    edu_html  = "".join(f"<p class='entry-text'>{_esc(ed.get('text',''))}</p>" for ed in education)
    proj_html = "".join(f"<p class='entry-text'>{_esc(pr.get('text',''))}</p>" for pr in projects)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{name} – Resume</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Lora:wght@400;600;700&family=Source+Sans+3:wght@400;600&display=swap');
  *{{margin:0;padding:0;box-sizing:border-box;}}
  body{{font-family:'Source Sans 3',serif;color:#111;background:#fff;padding:40px;max-width:800px;margin:0 auto;}}
  .name{{font-family:'Lora',serif;font-size:26px;font-weight:700;text-align:center;letter-spacing:1px;text-transform:uppercase;}}
  .role{{text-align:center;font-size:13px;color:#555;margin-top:3px;}}
  .contact{{text-align:center;font-size:11px;color:#555;margin-top:6px;}}
  hr.thick{{border:none;border-top:2px solid #111;margin:14px 0 10px;}}
  hr.thin{{border:none;border-top:1px solid #ccc;margin:8px 0;}}
  .sec-title{{font-family:'Lora',serif;font-size:13px;font-weight:700;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;}}
  .section{{margin-bottom:16px;}}
  .summary,.entry-text,.additional{{font-size:12px;line-height:1.7;color:#333;}}
  .skills-list{{font-size:12px;color:#333;}}
  .cert-list{{list-style:none;font-size:12px;color:#333;}}
  .cert-list li::before{{content:"• ";}}
  @media print{{body{{padding:20px;}}}}
</style>
</head>
<body>
  <div class="name">{name}</div>
  <div class="role">{role}</div>
  <div class="contact">{" | ".join(contact_parts)}</div>
  <hr class="thick">
  {"<div class='section'><div class='sec-title'>Professional Summary</div><hr class='thin'><p class='summary'>" + summary + "</p></div>" if summary else ""}
  {"<div class='section'><div class='sec-title'>Skills</div><hr class='thin'><p class='skills-list'>" + " • ".join(_esc(s) for s in skills) + "</p></div>" if skills else ""}
  {"<div class='section'><div class='sec-title'>Work Experience</div><hr class='thin'>" + exp_html + "</div>" if exp_html else ""}
  {"<div class='section'><div class='sec-title'>Education</div><hr class='thin'>" + edu_html + "</div>" if edu_html else ""}
  {"<div class='section'><div class='sec-title'>Projects</div><hr class='thin'>" + proj_html + "</div>" if proj_html else ""}
  {"<div class='section'><div class='sec-title'>Certifications</div><hr class='thin'><ul class='cert-list'>" + "".join(f"<li>{_esc(c)}</li>" for c in certifications) + "</ul></div>" if certifications else ""}
  {"<div class='section'><div class='sec-title'>Additional</div><hr class='thin'><p class='additional'>" + additional + "</p></div>" if additional else ""}
</body>
</html>"""


def render_minimal(d):
    name  = _esc(d.get("name", "Your Name"))
    role  = _esc(d.get("job_role", "Professional"))
    email = _esc(d.get("email", ""))
    phone = _esc(d.get("phone", ""))
    linkedin = _esc(d.get("linkedin", ""))
    github   = _esc(d.get("github", ""))
    summary  = _esc(d.get("summary", ""))
    skills   = d.get("skills", [])
    experience     = d.get("experience", [])
    education      = d.get("education", [])
    projects       = d.get("projects", [])
    certifications = d.get("certifications", [])
    additional     = _esc(d.get("additional", ""))

    contact_parts = [x for x in [email, phone, linkedin, github] if x]
    exp_html  = "".join(f"<p class='entry'>{_esc(ex.get('text',''))}</p>" for ex in experience)
    edu_html  = "".join(f"<p class='entry'>{_esc(ed.get('text',''))}</p>" for ed in education)
    proj_html = "".join(f"<p class='entry'>{_esc(pr.get('text',''))}</p>" for pr in projects)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{name} – Resume</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&display=swap');
  *{{margin:0;padding:0;box-sizing:border-box;}}
  body{{font-family:'DM Sans',sans-serif;color:#1a1a1a;background:#fff;padding:48px;max-width:800px;margin:0 auto;}}
  .name{{font-size:32px;font-weight:600;letter-spacing:-0.5px;}}
  .role{{font-size:15px;color:#00897B;font-weight:500;margin-top:4px;}}
  .divider{{width:40px;height:3px;background:#00897B;margin:14px 0;border-radius:2px;}}
  .contact{{font-size:12px;color:#666;display:flex;gap:16px;flex-wrap:wrap;margin-bottom:28px;}}
  .section{{margin-bottom:22px;}}
  .sec-title{{font-size:10px;font-weight:600;letter-spacing:2px;text-transform:uppercase;color:#00897B;margin-bottom:8px;}}
  .summary{{font-size:13px;line-height:1.8;color:#444;}}
  .skills-wrap{{display:flex;flex-wrap:wrap;gap:8px;}}
  .skill-tag{{font-size:11px;color:#00897B;border:1px solid #00897B;padding:2px 10px;border-radius:4px;}}
  .entry{{font-size:12px;line-height:1.7;color:#444;margin-bottom:8px;}}
  .cert-list{{list-style:none;font-size:12px;color:#444;}}
  .cert-list li{{padding:2px 0;}}
  .cert-list li::before{{content:"→ ";color:#00897B;}}
  .additional{{font-size:12px;color:#444;line-height:1.7;}}
  @media print{{body{{padding:28px;}}}}
</style>
</head>
<body>
  <div class="name">{name}</div>
  <div class="role">{role}</div>
  <div class="divider"></div>
  <div class="contact">{" · ".join(contact_parts)}</div>
  {"<div class='section'><div class='sec-title'>About</div><p class='summary'>" + summary + "</p></div>" if summary else ""}
  {"<div class='section'><div class='sec-title'>Skills</div><div class='skills-wrap'>" + "".join(f"<span class='skill-tag'>{_esc(s)}</span>" for s in skills) + "</div></div>" if skills else ""}
  {"<div class='section'><div class='sec-title'>Experience</div>" + exp_html + "</div>" if exp_html else ""}
  {"<div class='section'><div class='sec-title'>Education</div>" + edu_html + "</div>" if edu_html else ""}
  {"<div class='section'><div class='sec-title'>Projects</div>" + proj_html + "</div>" if proj_html else ""}
  {"<div class='section'><div class='sec-title'>Certifications</div><ul class='cert-list'>" + "".join(f"<li>{_esc(c)}</li>" for c in certifications) + "</ul></div>" if certifications else ""}
  {"<div class='section'><div class='sec-title'>Additional</div><p class='additional'>" + additional + "</p></div>" if additional else ""}
</body>
</html>"""


TEMPLATE_RENDERERS = {
    "modern":  render_modern,
    "classic": render_classic,
    "minimal": render_minimal,
}


# ──────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("assistant.html")


@app.route("/assistant")
def assistant():
    from flask import redirect
    return redirect("/")


@app.route("/template/list", methods=["GET"])
def template_list():
    return jsonify([
        {"id": "modern",  "name": "Modern",  "description": "Blue gradient header with colored skill badges — sleek and contemporary.", "accent": "#0066cc", "number": "1"},
        {"id": "classic", "name": "Classic", "description": "Traditional professional layout — clean, conservative, and timeless.",      "accent": "#1a1a1a", "number": "2"},
        {"id": "minimal", "name": "Minimal", "description": "Clean lines with a teal accent — modern minimalism that stands out.",       "accent": "#00897B", "number": "3"},
    ])


@app.route("/parse", methods=["POST"])
def parse_endpoint():
    """Standalone field parser — useful for testing individual fields."""
    data  = request.get_json() or {}
    field = data.get("field", "").lower()
    text  = (data.get("text", "") or "").strip()
    print(f"\n[PARSE] field={field}, text={text}")

    parsed = parse_with_groq(field, text) or {}
    print(f"[RESULT] {parsed}\n")
    return jsonify(parsed)


# ────── Conversation endpoints ──────

@app.route("/conversation/init", methods=["GET"])
def conversation_init():
    session = convman.create_session()
    step    = convman.get_current_step(session["session_id"])
    return jsonify({
        "session_id": session["session_id"],
        "step_id":    step["id"],
        "question":   step["q"],
        "data":       session["data"],
    })


@app.route("/conversation/next", methods=["GET"])
def conversation_next():
    sid = request.args.get("session_id")
    if not sid:
        return jsonify({"error": "session_id required"}), 400
    step = convman.get_current_step(sid)
    if not step:
        return jsonify({"error": "no session"}), 404
    return jsonify({
        "session_id": sid,
        "step_id":    step["id"],
        "question":   step["q"],
        "data":       convman.get_session(sid)["data"],
    })


@app.route("/conversation/submit", methods=["POST"])
def conversation_submit():
    payload = request.get_json() or {}
    sid  = payload.get("session_id")
    text = payload.get("text", "").strip()

    if not sid:
        return jsonify({"error": "session_id required"}), 400

    session = convman.get_session(sid)
    if not session:
        return jsonify({"error": "invalid session_id"}), 404

    current_step = convman.get_current_step(sid)
    step_field   = current_step.get("field") if current_step else None
    print(f"\n[CONV] session={sid[:8]}, step={step_field}, text={text}")

    # ── Save raw answer first (session controller handles basic field routing) ──
    convman.submit_answer(sid, text)

    # ── Groq-powered enrichment for all structured fields ──
    try:
        if step_field and text:
            parsed = parse_with_groq(step_field, text)

            if parsed:
                data = session["data"]

                if step_field == "name" and parsed.get("name"):
                    data["name"] = parsed["name"]

                elif step_field == "contact":
                    if parsed.get("email"):
                        data["email"] = parsed["email"]
                    if parsed.get("phone"):
                        data["phone"] = parsed["phone"]

                elif step_field == "education":
                    # Build a clean readable string AND store structured data
                    parts = []
                    if parsed.get("degree"):  parts.append(parsed["degree"])
                    if parsed.get("field"):   parts.append(f"in {parsed['field']}")
                    if parsed.get("institution"): parts.append(f"from {parsed['institution']}")
                    if parsed.get("year"):    parts.append(f"({parsed['year']})")
                    if parsed.get("cgpa"):    parts.append(f"CGPA: {parsed['cgpa']}")
                    display = " ".join(parts) if parts else text
                    # Replace last appended raw entry with structured one
                    if data["education"]:
                        data["education"][-1] = {"text": display, "structured": parsed}
                    else:
                        data["education"] = [{"text": display, "structured": parsed}]

                elif step_field == "experience":
                    parts = []
                    if parsed.get("role"):    parts.append(parsed["role"])
                    if parsed.get("company"): parts.append(f"at {parsed['company']}")
                    if parsed.get("startYear"):
                        yr = parsed["startYear"]
                        if parsed.get("endYear"): yr += f" – {parsed['endYear']}"
                        parts.append(f"({yr})")
                    display = " ".join(parts) if parts else text
                    if data["experience"]:
                        data["experience"][-1] = {"text": display, "structured": parsed}
                    else:
                        data["experience"] = [{"text": display, "structured": parsed}]

                elif step_field == "projects":
                    parts = []
                    if parsed.get("title"):       parts.append(parsed["title"])
                    if parsed.get("description"): parts.append(f"— {parsed['description']}")
                    if parsed.get("tech"):        parts.append(f"[{parsed['tech']}]")
                    display = " ".join(parts) if parts else text
                    if data["projects"]:
                        data["projects"][-1] = {"text": display, "structured": parsed}
                    else:
                        data["projects"] = [{"text": display, "structured": parsed}]

                elif step_field == "skills" and parsed.get("skills"):
                    data["skills"] = parsed["skills"]

                elif step_field == "certifications" and parsed.get("certifications"):
                    data["certifications"] = parsed["certifications"]

                elif step_field == "linkedin" and parsed.get("url"):
                    data["linkedin"] = parsed["url"]

                elif step_field == "github" and parsed.get("url"):
                    data["github"] = parsed["url"]

                elif step_field in ("job_role", "summary", "additional"):
                    # Use raw text directly — no restructuring needed
                    pass

    except Exception as e:
        print(f"[CONV GROQ ERROR] {e}")

    # Advance to next step
    convman.advance(sid)
    next_step = convman.get_current_step(sid)

    return jsonify({
        "session_id": sid,
        "step_id":    next_step["id"] if next_step else "done",
        "question":   next_step["q"]  if next_step else "",
        "data":       session["data"],
        "completed":  session["completed"],
    })


@app.route("/conversation/status", methods=["GET"])
def conversation_status():
    sid = request.args.get("session_id")
    if not sid:
        return jsonify({"error": "session_id required"}), 400
    s = convman.get_session(sid)
    if not s:
        return jsonify({"error": "invalid session"}), 404
    return jsonify(s)


# ────── Resume endpoints ──────

@app.route("/resume/preview", methods=["POST"])
def resume_preview():
    data        = request.get_json() or {}
    template_id = data.get("template", "modern")
    renderer    = TEMPLATE_RENDERERS.get(template_id, render_modern)
    return jsonify({"html": renderer(data)})


@app.route("/resume/export", methods=["POST"])
def resume_export():
    data        = request.get_json() or {}
    template_id = data.get("template", "modern")
    renderer    = TEMPLATE_RENDERERS.get(template_id, render_modern)
    html        = renderer(data)
    name        = data.get("name", "Resume").replace(" ", "_")
    return Response(
        html,
        mimetype="text/html",
        headers={"Content-Disposition": f'attachment; filename="{name}_Resume.html"'},
    )


# ────── Transcription endpoint (Groq Whisper) ──────

@app.route("/transcribe", methods=["POST"])
def transcribe_endpoint():
    """
    Accept an audio file upload, transcribe it with Groq Whisper,
    and optionally parse the resulting text for the given field.
    """
    if "file" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    f     = request.files["file"]
    field = (request.form.get("field") or request.args.get("field") or "").lower()

    try:
        client = get_groq_client()
        audio_bytes = f.read()
        filename    = f.filename or "audio.webm"

        # Groq Whisper transcription
        transcription = client.audio.transcriptions.create(
            file=(filename, audio_bytes, f.mimetype or "audio/webm"),
            model="whisper-large-v3-turbo",
            response_format="verbose_json",
            language="en",
        )
        text = (transcription.text or "").strip()
        print(f"[TRANSCRIBE] field={field}, transcript={text}")

    except Exception as e:
        print(f"[TRANSCRIBE ERROR] {e}")
        return jsonify({"error": f"Transcription failed: {str(e)}"}), 500

    # Optionally parse the transcript for the given field
    parsed = parse_with_groq(field, text) if field else {}

    return jsonify({"text": text, "parsed": parsed or {}})


# ────── Health check ──────

@app.route("/health")
def health():
    key = os.environ.get("GROQ_API_KEY", "")
    return jsonify({
        "status": "ok",
        "groq_key_set": bool(key) and key != "YOUR_GROQ_API_KEY_HERE",
    })


if __name__ == "__main__":
    print("=" * 55)
    print("  Voice Resume AI — Groq-powered backend")
    print("=" * 55)
    key = os.environ.get("GROQ_API_KEY", "")
    if not key or key == "YOUR_GROQ_API_KEY_HERE":
        print("⚠️  WARNING: GROQ_API_KEY not set! Edit your .env file.")
    else:
        print(f"✅ GROQ_API_KEY present ({key[:8]}...)")
    print("🚀 Starting at http://127.0.0.1:5000")
    print("=" * 55)
    app.run(host="127.0.0.1", port=5000, debug=False)
