# conversation_controller.py
# Enhanced in-memory conversation manager for voice resume assistant.
# Includes template selection, projects, certifications, LinkedIn/GitHub fields.
import uuid
import re
from typing import Dict, Any


class ConversationManager:
    def __init__(self):
        # session_id -> session data
        self.sessions: Dict[str, Dict[str, Any]] = {}

        # Full conversation flow with extra fields
        self.flow = [
            {
                "id": "greeting",
                "q": (
                    "Hello! Welcome to Resume AI, your voice-powered resume builder. "
                    "I'm here to help you craft a professional resume just by talking to me. "
                    "This tool is designed to be fully accessible — everything works by voice. "
                    "Ready to get started? Please say yes to continue."
                ),
                "field": None,
                "optional": False,
            },
            {
                "id": "template",
                "q": (
                    "Great! First, let's pick a resume style. I have three beautiful templates for you. "
                    "Say ONE for a Modern blue gradient style. "
                    "Say TWO for a Classic professional style. "
                    "Say THREE for a Clean minimal style. "
                    "Which one do you prefer?"
                ),
                "field": "template",
                "optional": False,
            },
            {
                "id": "name",
                "q": "What is your full name?",
                "field": "name",
                "optional": False,
            },
            {
                "id": "contact",
                "q": (
                    "What's your email address and phone number? "
                    "You can say them together. For example: "
                    "my email is john at gmail dot com and my number is 9876543210."
                ),
                "field": "contact",
                "optional": False,
            },
            {
                "id": "linkedin",
                "q": (
                    "Do you have a LinkedIn profile URL? "
                    "You can spell it out or say your LinkedIn username. "
                    "For example: linkedin dot com slash in slash john-doe. "
                    "Or say skip to continue."
                ),
                "field": "linkedin",
                "optional": True,
            },
            {
                "id": "github",
                "q": (
                    "Do you have a GitHub or portfolio website? "
                    "You can say the URL or just your GitHub username. "
                    "Or say skip to continue."
                ),
                "field": "github",
                "optional": True,
            },
            {
                "id": "job_role",
                "q": (
                    "What is your current job title or the role you're applying for? "
                    "For example: Software Engineer, Data Scientist, or Marketing Manager."
                ),
                "field": "job_role",
                "optional": False,
            },
            {
                "id": "summary",
                "q": (
                    "Tell me about yourself in two or three sentences. "
                    "What are you passionate about and what value do you bring?"
                ),
                "field": "summary",
                "optional": False,
            },
            {
                "id": "skills",
                "q": (
                    "What are your key technical or professional skills? "
                    "List them by saying AND between each one. "
                    "For example: Python and React and Machine Learning and Communication."
                ),
                "field": "skills",
                "optional": False,
            },
            {
                "id": "experience",
                "q": (
                    "Describe your most recent work experience. "
                    "Include your job title, company name, and years. "
                    "For example: I was a Software Developer at Infosys from 2021 to 2024. "
                    "Say skip if you have no work experience yet."
                ),
                "field": "experience",
                "optional": True,
            },
            {
                "id": "education",
                "q": (
                    "Tell me about your education. "
                    "What degree, from which college or university, and when did you graduate? "
                    "For example: B.Tech in Computer Science from Rajalakshmi Institute of Technology, 2024."
                ),
                "field": "education",
                "optional": False,
            },
            {
                "id": "projects",
                "q": (
                    "Tell me about a project you've worked on. "
                    "Include the project name, what it does, and the technologies used. "
                    "For example: I built a Voice Resume Builder using Python, Flask, and Web Speech API. "
                    "Say skip if you'd like to leave this blank."
                ),
                "field": "projects",
                "optional": True,
            },
            {
                "id": "certifications",
                "q": (
                    "Do you have any certifications or courses you'd like to include? "
                    "For example: AWS Certified Developer, Google Data Analytics, or Coursera Machine Learning. "
                    "Say skip to continue."
                ),
                "field": "certifications",
                "optional": True,
            },
            {
                "id": "additional",
                "q": (
                    "Any other achievements, languages spoken, volunteer work, or hobbies to mention? "
                    "Say skip if you have nothing to add."
                ),
                "field": "additional",
                "optional": True,
            },
            {
                "id": "preview",
                "q": (
                    "Excellent! I now have everything I need. "
                    "Let me build your resume right now. Just a moment..."
                ),
                "field": None,
                "optional": False,
            },
            {
                "id": "done",
                "q": (
                    "Your resume is ready! You can see it on screen. "
                    "Use the Export PDF button to download it, "
                    "or say restart to build a new one."
                ),
                "field": None,
                "optional": False,
            },
        ]

    def create_session(self) -> Dict[str, Any]:
        sid = str(uuid.uuid4())
        self.sessions[sid] = {
            "session_id": sid,
            "current_index": 0,
            "data": {
                "template": "modern",
                "name": "",
                "email": "",
                "phone": "",
                "linkedin": "",
                "github": "",
                "job_role": "",
                "summary": "",
                "skills": [],
                "experience": [],
                "education": [],
                "projects": [],
                "certifications": [],
                "additional": "",
            },
            "completed": False,
        }
        return self.sessions[sid]

    def get_session(self, sid: str) -> Dict[str, Any]:
        return self.sessions.get(sid)

    def get_current_step(self, sid: str) -> Dict[str, Any]:
        s = self.get_session(sid)
        if not s:
            return None
        idx = s["current_index"]
        if idx >= len(self.flow):
            return {"id": "done", "q": "", "field": None, "optional": False}
        return self.flow[idx]

    def advance(self, sid: str):
        s = self.get_session(sid)
        if not s:
            return
        s["current_index"] += 1
        if s["current_index"] >= len(self.flow):
            s["completed"] = True

    def _is_skip(self, text: str) -> bool:
        """Return True if the user said skip / none / no / nothing / nope."""
        clean = text.strip().lower()
        return clean in {"skip", "none", "no", "nothing", "nope", "n/a", "na", "don't have", "i don't have"}

    def submit_answer(self, sid: str, text: str):
        """Store the user's answer into the appropriate data field."""
        s = self.get_session(sid)
        if not s:
            return None
        step = self.get_current_step(sid)
        if not step:
            return None
        field = step.get("field")
        if not field:
            return s

        # Handle skip for optional fields
        if step.get("optional") and self._is_skip(text):
            # Leave field as default (empty / [])
            return s

        # Field-specific handling
        if field == "template":
            s["data"]["template"] = self._parse_template(text)

        elif field == "skills":
            parts = [p.strip().title() for p in self.__split_skills(text) if p.strip()]
            s["data"]["skills"] = parts

        elif field == "contact":
            s["data"]["email"] = self.__extract_email(text)
            s["data"]["phone"] = self.__extract_phone(text)

        elif field == "experience":
            if not isinstance(s["data"]["experience"], list):
                s["data"]["experience"] = []
            s["data"]["experience"].append({"text": text})

        elif field == "education":
            if not isinstance(s["data"]["education"], list):
                s["data"]["education"] = []
            s["data"]["education"].append({"text": text})

        elif field == "projects":
            if not isinstance(s["data"]["projects"], list):
                s["data"]["projects"] = []
            s["data"]["projects"].append({"text": text})

        elif field == "certifications":
            if not isinstance(s["data"]["certifications"], list):
                s["data"]["certifications"] = []
            # Split on comma/and
            parts = re.split(r",\s*|\s+and\s+", text, flags=re.IGNORECASE)
            for p in parts:
                p = p.strip()
                if p and not self._is_skip(p):
                    s["data"]["certifications"].append(p)

        elif field == "linkedin":
            s["data"]["linkedin"] = self._clean_url(text, "linkedin.com/in/")

        elif field == "github":
            s["data"]["github"] = self._clean_url(text, "github.com/")

        else:
            # Direct field assignment (name, job_role, summary, additional)
            s["data"][field] = text.strip()

        return s

    # ────────── helpers ──────────

    def _parse_template(self, text: str) -> str:
        t = text.strip().lower()
        if any(w in t for w in ["one", "1", "modern", "blue", "first"]):
            return "modern"
        if any(w in t for w in ["two", "2", "classic", "traditional", "second"]):
            return "classic"
        if any(w in t for w in ["three", "3", "minimal", "clean", "third", "simple"]):
            return "minimal"
        return "modern"  # default

    def _clean_url(self, text: str, prefix: str) -> str:
        """Try to extract a URL or build one from username."""
        t = text.strip()
        # Replace spoken "dot com" etc.
        t = re.sub(r"\s+dot\s+", ".", t, flags=re.I)
        t = re.sub(r"\s+slash\s+", "/", t, flags=re.I)
        t = re.sub(r"\s+", "", t)  # remove spaces
        if "http" in t:
            return t
        if prefix.split("/")[0] in t:
            return "https://" + t
        # Treat as username
        return f"https://{prefix}{t}"

    def __split_skills(self, text: str) -> list:
        parts = re.split(r"\s+and\s+|,\s*", text, flags=re.IGNORECASE)
        return [p.strip() for p in parts if p.strip()]

    def __extract_email(self, text: str) -> str:
        # Handle spoken email: "john dot doe at gmail dot com"
        t = text
        t = re.sub(r"\s+at\s+(gmail|yahoo|outlook|hotmail|icloud)\b", r" @ \1", t, flags=re.I)
        t = re.sub(r"\s+at\s+", " @ ", t, flags=re.I)
        t = re.sub(r"\s+dot\s+", ".", t, flags=re.I)
        t = re.sub(r"\s+underscore\s+", "_", t, flags=re.I)
        match = re.search(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", t)
        return match.group(0).lower() if match else ""

    def __extract_phone(self, text: str) -> str:
        digits = re.sub(r"[^\d+]", "", text)
        if len(re.sub(r"[^\d]", "", digits)) >= 8:
            return digits
        match = re.search(r"[\d\s\-().+]{7,}", text)
        if match:
            phone = match.group(0).strip()
            return phone if len(phone) >= 7 else ""
        return ""
