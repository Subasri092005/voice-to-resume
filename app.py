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
            "Return only the name in title case, max 4 words. "
            "Remove ALL filler: 'my name is', 'I am', 'this is', 'myself', 'I'm called', 'hey', 'hi'. "
            "IMPORTANT: Preserve the EXACT name even if it sounds unusual. "
            "Indian names, non-English names, and uncommon spellings must be kept as spoken. "
            "Examples: 'my name is Subasri' → 'Subasri', 'I am Parvathi Devi' → 'Parvathi Devi', "
            "'myself Rahul Kumar' → 'Rahul Kumar', 'hi my name is Arun' → 'Arun'. "
            "Do NOT autocorrect or change the name to a more common English name. "
        ),
    },
    "email": {
        "schema": '{"email": "example@domain.com"}',
        "instruction": (
            "Extract ONLY the email address from the spoken text. "
            "RULES: "
            "- 'at the rate', 'at', '@' → '@' "
            "- 'dot', 'period', 'point' → '.' "
            "- 'underscore', 'under score' → '_' "
            "- 'hyphen', 'dash' → '-' "
            "Examples: "
            "- 'john dot doe at gmail dot com' → 'john.doe@gmail.com' "
            "- 'subasri underscore 09 at gmail dot com' → 'subasri_09@gmail.com' "
            "- 'rahul123 at yahoo dot co dot in' → 'rahul123@yahoo.co.in' "
            "Return ONLY the email string. If no email found, return empty string."
        ),
    },
    "phone": {
        "schema": '{"phone": "9876543210"}',
        "instruction": (
            "Extract ONLY the phone number digits from the spoken text. "
            "RULES: "
            "- Convert spoken digit words: 'nine eight seven' → '987' "
            "- 'double nine' → '99', 'triple eight' → '888' "
            "- 'plus nine one' at start → '+91' "
            "- Remove ALL non-digit characters EXCEPT a leading '+' "
            "- The user may say 'my number is 9876543210' → return '9876543210' "
            "- The user may say 'nine double zero triple three eight two zero zero' → return '90003382000' "
            "Return ONLY the digit string. If no phone found, return empty string."
        ),
    },
    "education": {
        "schema": '{"institution": "<university name>", "degree": "<B.Tech/M.Sc/etc>", "field": "<subject>", "cgpa": "<number>", "year": "<graduation year>"}',
        "instruction": (
            "Extract ONLY the key education details from the spoken text. "
            "The user may speak in a long conversational way — IGNORE all filler words, "
            "personal stories, and opinions. Extract ONLY: "
            "1. Institution/university name "
            "2. Degree type (B.Tech, M.Tech, B.Sc, M.Sc, BCA, MCA, MBA, Diploma, B.E., etc.) "
            "3. Field of study (Computer Science, ECE, EEE, Mechanical, etc.) "
            "4. CGPA/GPA/percentage (just the number) "
            "5. Graduation year (just the year) "
            "Example: 'So basically I studied at VIT university in Vellore and I did my "
            "B.Tech in Computer Science and I graduated in 2024 with a CGPA of 8.5' "
            "→ {\"institution\": \"VIT University\", \"degree\": \"B.Tech\", \"field\": \"Computer Science\", "
            "\"cgpa\": \"8.5\", \"year\": \"2024\"} "
            "Leave any genuinely missing fields as empty string. "
        ),
    },
    "skills": {
        "schema": '{"skills": ["Skill One", "Skill Two", "Skill Three"]}',
        "instruction": (
            "Extract individual technical and professional skills from the spoken text. "
            "Return ONLY skill names — remove ALL filler like 'my skills are', 'I know', "
            "'I am good at', 'I have experience in', 'basically', 'also'. "
            "Return each as a separate item in the list. Title case each skill. "
            "Common separators: 'and', commas, '/', '+'. "
            "Example: 'So my skills are basically Python and also I know React and "
            "I'm good at machine learning and communication' "
            "→ [\"Python\", \"React\", \"Machine Learning\", \"Communication\"] "
        ),
    },
    "experience": {
        "schema": '{"role": "<Job Title>", "company": "<Company/Org Name>", "department": "<Dept/Field, if mentioned>", "startYear": "<YYYY>", "endYear": "<YYYY or present>"}',
        "instruction": (
            "Extract ONLY these key fields from the spoken experience. "
            "Ignore ALL filler words, stories, and opinions. "
            "1. Job title / role "
            "2. Company or organization name "
            "3. Department or field (e.g., CSE, ECE, Sales) — if mentioned, else empty "
            "4. Start year "
            "5. End year (or 'present' if still working) "
            "Example: 'I have worked as assistant professor in RIT in the dept of CSE from 2020 to 2023' "
            "→ {\"role\": \"Assistant Professor\", \"company\": \"RIT\", \"department\": \"CSE\", \"startYear\": \"2020\", \"endYear\": \"2023\"} "
            "Example: 'Worked at TCS as software engineer since 2022' "
            "→ {\"role\": \"Software Engineer\", \"company\": \"TCS\", \"department\": \"\", \"startYear\": \"2022\", \"endYear\": \"present\"} "
            "Leave genuinely missing fields as empty string. "
        ),
    },
    "projects": {
        "schema": '{"title": "<project name>", "description": "<1-2 sentence summary>", "tech": "<technologies used>"}',
        "instruction": (
            "Extract ONLY the key project details from the spoken text. "
            "The user may describe the project at length — CONDENSE it: "
            "1. Project title/name "
            "2. A brief 1-2 sentence summary of what it does (NOT a transcript of what they said) "
            "3. Technologies/tools used (comma separated) "
            "Example: 'I built this really cool project called Voice Resume Builder where basically "
            "you can speak and it builds your resume automatically. I used Python for the backend "
            "and Flask as the framework and also JavaScript for the frontend and the Web Speech API "
            "for voice recognition.' "
            "→ {\"title\": \"Voice Resume Builder\", \"description\": \"A voice-powered tool that "
            "builds professional resumes through speech input.\", "
            "\"tech\": \"Python, Flask, JavaScript, Web Speech API\"} "
            "Leave missing fields as empty string. "
        ),
    },
    "certifications": {
        "schema": '{"certifications": ["Cert One", "Cert Two"]}',
        "instruction": (
            "Extract certification/course names from the spoken text. "
            "Remove ALL filler: 'I completed', 'I have done', 'I got certified in', 'basically'. "
            "Return ONLY the certification names as a list. "
            "Example: 'I completed AWS Certified Developer and also I did Google Data Analytics "
            "from Coursera' → [\"AWS Certified Developer\", \"Google Data Analytics\"] "
        ),
    },
    "summary": {
        "schema": '{"summary": "<2-3 sentence professional summary>"}',
        "instruction": (
            "Convert the user's spoken self-description into a POLISHED professional summary "
            "of 2-3 sentences suitable for a resume. "
            "Remove filler words, repeated phrases, and informal language. "
            "Write in third person or first person professional tone. "
            "Example input: 'So basically I am a software developer with like 3 years experience "
            "and I love building web apps and I'm passionate about AI and machine learning' "
            "→ 'Passionate software developer with 3 years of experience specializing in web "
            "application development. Skilled in AI and machine learning technologies.' "
        ),
    },
    "job_role": {
        "schema": '{"role": "<Job Title>"}',
        "instruction": (
            "Extract the job title or role from the spoken text. "
            "Remove ALL filler: 'I am a', 'I work as', 'my role is', 'basically'. "
            "Return ONLY the job title in proper format. "
            "Example: 'I am working as a full stack developer' → 'Full Stack Developer' "
            "Example: 'So basically I'm a data scientist' → 'Data Scientist' "
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
    "additional": {
        "schema": '{"value": "<cleaned text>"}',
        "instruction": (
            "Clean up the user's spoken text about additional information (hobbies, languages, "
            "volunteer work, achievements). Remove filler words and present cleanly. "
            "Example: 'So basically I speak English and Tamil and also I do volunteering at a local NGO' "
            "→ 'Languages: English, Tamil. Volunteer work at local NGO.' "
        ),
    },
}

GENERIC_PROMPT = {
    "schema": '{"value": "<extracted text>"}',
    "instruction": "Clean up and return the most meaningful text from the user's spoken input.",
}


def translate_to_english(text: str) -> str:
    """
    Translate Tamil (or any non-English) text to English using Groq LLM.
    Returns the English translation. If translation fails, returns original text.
    """
    if not text or not text.strip():
        return text

    try:
        client = get_groq_client()
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a translator. Translate the given Tamil text to English. "
                        "If the text is already in English, return it as-is. "
                        "If the text is a mix of Tamil and English, translate only the Tamil parts. "
                        "IMPORTANT: Preserve proper nouns, names, company names, technical terms, "
                        "email addresses, phone numbers, and URLs exactly as they are. "
                        "Return ONLY the translated text, nothing else. No quotes, no explanation."
                    ),
                },
                {"role": "user", "content": text},
            ],
            temperature=0,
            max_tokens=500,
        )
        translated = response.choices[0].message.content.strip()
        print(f"[TRANSLATE] '{text}' → '{translated}'")
        return translated if translated else text
    except Exception as e:
        print(f"[TRANSLATE ERROR] {e}")
        return text


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
            "The input comes from speech recognition and may contain errors. "
            "IMPORTANT — BILINGUAL SUPPORT: The user may speak in Tamil, English, or a mix of both. "
            "If the input is in Tamil (தமிழ்) or has Tamil words, TRANSLATE everything to English first, "
            "then extract the fields. The output JSON must ALWAYS be in English. "
            "SPOKEN CONVENTIONS the user may use: "
            "'dot' or 'period' = '.', 'at' or 'at the rate' = '@', "
            "'slash' = '/', 'underscore' or 'under score' = '_', "
            "'hyphen' or 'dash' = '-', 'space' = ' '. "
            "SPOKEN NUMBERS: 'one'='1','two'='2','three'='3','four'='4','five'='5',"
            "'six'='6','seven'='7','eight'='8','nine'='9','zero'='0', "
            "'double X' = 'XX', 'triple X' = 'XXX'. "
            "IMPORTANT: Preserve names exactly as spoken — do NOT correct unusual "
            "or non-English names to common English words. "
            "Return ONLY a valid JSON object in exactly this shape: "
            f"{meta['schema']}. "
            "No explanation, no markdown, no extra text. Only the JSON object."
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

# Filler patterns to strip when Groq fails and we use raw text as fallback
_FILLER_RE = re.compile(
    r"^\s*(so\s+)?basically\s*|"
    r"^\s*i\s+(have\s+)?(worked|work|was|am|am\s+a|have\s+been)\s+(as\s+|at\s+|in\s+)?|"
    r"^\s*(my|the)\s+(name\s+is|role\s+is|job\s+is|title\s+is)\s+|"
    r"^\s*(i\s+(am|m)\s+(a\s+)?|i\s+am\s+currently\s+(a\s+)?)|"
    r"^\s*(so\s+|well\s+|actually\s+|basically\s+)+",
    re.IGNORECASE,
)

def _smart_clean(text: str) -> str:
    """Strip common spoken filler from the start of a sentence as a fallback."""
    cleaned = _FILLER_RE.sub("", text.strip())
    # Capitalize first letter
    return cleaned[:1].upper() + cleaned[1:] if cleaned else text.strip()

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
    sid = session["session_id"]
    question = convman.get_current_question(sid)
    step    = convman.get_current_step(sid)
    return jsonify({
        "session_id": sid,
        "step_id":    step["id"],
        "question":   question,
        "language":   session.get("language", "en"),
        "data":       session["data"],
    })


@app.route("/conversation/next", methods=["GET"])
def conversation_next():
    sid = request.args.get("session_id")
    if not sid:
        return jsonify({"error": "session_id required"}), 400
    
    session = convman.get_session(sid)
    if not session:
        return jsonify({"error": "no session"}), 404
    
    step = convman.get_current_step(sid)
    question = convman.get_current_question(sid)
    lang = session.get("language", "en")

    return jsonify({
        "session_id": sid,
        "step_id":    step["id"],
        "question":   question,
        "language":   lang,
        "data":       session["data"],
    })


@app.route("/conversation/set-language", methods=["POST"])
def conversation_set_language():
    """
    Switch language mid-conversation and return current question in new language.
    Useful for the language button toggle.
    """
    payload = request.get_json() or {}
    sid = payload.get("session_id")
    new_lang = payload.get("language", "en")  # "en" or "ta"
    
    if not sid:
        return jsonify({"error": "session_id required"}), 400
    
    session = convman.get_session(sid)
    if not session:
        return jsonify({"error": "invalid session_id"}), 404
    
    # Update language
    session["language"] = "ta" if new_lang == "ta" else "en"
    print(f"[LANG SWITCH] session={sid[:8]}, new_lang={session['language']}")
    
    # Get current question in the new language
    step = convman.get_current_step(sid)
    question = convman.get_current_question(sid)
    
    return jsonify({
        "session_id": sid,
        "step_id":    step["id"],
        "question":   question,
        "language":   session["language"],
        "data":       session["data"],
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

    # Get language from session
    lang = session.get("language", "en")
    
    current_step = convman.get_current_step(sid)
    step_field   = current_step.get("field") if current_step else None
    print(f"\n[CONV] session={sid[:8]}, step={step_field}, lang={lang}, text={text}")

    # ── If Tamil mode, translate the answer to English first ──
    if lang == "ta" and text and step_field and step_field != "language":
        text = translate_to_english(text)
        print(f"[CONV] translated to English: {text}")

    # ── Save the (now English) answer ──
    convman.submit_answer(sid, text)

    # ── Groq-powered enrichment for all structured fields ──
    try:
        if step_field and text:
            parsed = parse_with_groq(step_field, text)

            if parsed:
                data = session["data"]

                if step_field == "name" and parsed.get("name"):
                    data["name"] = parsed["name"]

                elif step_field == "email" and parsed.get("email"):
                    data["email"] = parsed["email"]

                elif step_field == "phone" and parsed.get("phone"):
                    data["phone"] = parsed["phone"]

                elif step_field == "education":
                    # Compact dash-separated display
                    parts = []
                    if parsed.get("degree") and parsed.get("field"):
                        parts.append(f"{parsed['degree']} ({parsed['field']})")
                    elif parsed.get("degree"):
                        parts.append(parsed["degree"])
                    elif parsed.get("field"):
                        parts.append(parsed["field"])
                    if parsed.get("institution"): parts.append(parsed["institution"])
                    year_str = parsed.get("year", "")
                    if parsed.get("cgpa"): year_str = f"{year_str}, CGPA {parsed['cgpa']}" if year_str else f"CGPA {parsed['cgpa']}"
                    if year_str: parts.append(year_str)
                    display = " — ".join(parts) if parts else _smart_clean(text)
                    if data["education"]:
                        data["education"][-1] = {"text": display, "structured": parsed}
                    else:
                        data["education"] = [{"text": display, "structured": parsed}]

                elif step_field == "experience":
                    # Compact dash-separated display
                    parts = []
                    if parsed.get("role"):       parts.append(parsed["role"])
                    if parsed.get("company"):    parts.append(parsed["company"])
                    if parsed.get("department"): parts.append(parsed["department"])
                    # Year range
                    if parsed.get("startYear"):
                        yr = parsed["startYear"]
                        if parsed.get("endYear"): yr += f" – {parsed['endYear']}"
                        parts.append(yr)
                    display = " — ".join(parts) if parts else _smart_clean(text)
                    if data["experience"]:
                        data["experience"][-1] = {"text": display, "structured": parsed}
                    else:
                        data["experience"] = [{"text": display, "structured": parsed}]

                elif step_field == "projects":
                    parts = []
                    if parsed.get("title"):       parts.append(parsed["title"])
                    if parsed.get("description"): parts.append(parsed["description"])
                    if parsed.get("tech"):        parts.append(f"Tech: {parsed['tech']}")
                    display = " — ".join(parts) if parts else _smart_clean(text)
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

                elif step_field == "summary" and parsed.get("summary"):
                    data["summary"] = parsed["summary"]

                elif step_field == "job_role" and parsed.get("role"):
                    data["job_role"] = parsed["role"]

                elif step_field == "additional" and parsed.get("value"):
                    data["additional"] = parsed["value"]

    except Exception as e:
        print(f"[CONV GROQ ERROR] {e}")

    # Advance to next step
    convman.advance(sid)
    next_step = convman.get_current_step(sid)

    # Get the UPDATED language from session (in case user just selected it)
    updated_lang = session.get("language", "en")
    
    # Use the stored language from session
    next_question = convman.get_current_question(sid)

    return jsonify({
        "session_id": sid,
        "step_id":    next_step["id"] if next_step else "done",
        "question":   next_question,
        "language":   updated_lang,
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
    Can optionally use language preference from session if session_id is provided.
    """
    if "file" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    f     = request.files["file"]
    field = (request.form.get("field") or request.args.get("field") or "").lower()
    lang  = (request.form.get("language") or request.args.get("language") or "").lower()
    
    # If session_id provided and no explicit language, use session's language
    sid   = request.form.get("session_id") or request.args.get("session_id")
    if sid and not lang:
        session = convman.get_session(sid)
        if session:
            lang = session.get("language", "en")

    try:
        client = get_groq_client()
        audio_bytes = f.read()
        filename    = f.filename or "audio.webm"

        # Groq Whisper transcription — auto-detect language for bilingual support
        whisper_kwargs = {
            "file": (filename, audio_bytes, f.mimetype or "audio/webm"),
            "model": "whisper-large-v3-turbo",
            "response_format": "verbose_json",
        }
        # Only set language if explicitly English; omit for Tamil/auto-detect
        if lang == "en":
            whisper_kwargs["language"] = "en"
        elif lang == "ta":
            whisper_kwargs["language"] = "ta"
        # else: auto-detect

        transcription = client.audio.transcriptions.create(**whisper_kwargs)
        text = (transcription.text or "").strip()
        print(f"[TRANSCRIBE] field={field}, lang={lang}, transcript={text}")

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
