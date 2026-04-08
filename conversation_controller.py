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
                "id": "language",
                "q": (
                    "Hello! Welcome to Resume AI, your voice-powered resume builder. "
                    "Choose your language: Say ONE for English, or TWO for Tamil. "
                    "Which language would you prefer?"
                ),
                "q_ta": (
                    "வணக்கம்! குரல் மூலம் ரெச்சூம் உருவாக்கும் கருவிக்கு உங்களை வரவேற்கிறேன். "
                    "உங்கள் மொழியை தேர்வு செய்யுங்கள்: ஆங்கிலத்திற்கு ஒன்று, "
                    "தமிழுக்கு இரண்டு என்று சொல்லுங்கள். "
                    "நீங்கள் எந்த மொழியை விரும்புகிறீர்கள்?"
                ),
                "field": "language",
                "optional": False,
            },
            {
                "id": "greeting",
                "q": (
                    "Hello! Welcome to Resume AI, your voice-powered resume builder. "
                    "I'm here to help you craft a professional resume just by talking to me. "
                    "This tool is designed to be fully accessible — everything works by voice. "
                    "Ready to get started? Please say yes to continue."
                ),
                "q_ta": (
                    "வணக்கம்! குரல் மூலம் ரெச்சூம் உருவாக்கும் கருவிக்கு உங்களை வரவேற்கிறேன். "
                    "நான் உங்களுக்கு குரல் மூலமாக ஒரு தொழில்முறை ரெச்சூம் உருவாக்க உதவ இருக்கிறேன். "
                    "இது முழுமையாக குரல் மூலம் இயங்கும் வகையில் வடிவமைக்கப்பட்டுள்ளது. "
                    "தொடங்க தயாரா? ஆமா என்று சொல்லுங்கள்."
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
                "q_ta": (
                    "நன்று! முதலில் ஒரு ரெஸ்யூம் வடிவமைப்பை தேர்வு செய்யலாம். "
                    "மூன்று அழகான வடிவமைப்புகள் உள்ளன. "
                    "நவீன நீல வடிவமைப்புக்கு ஒன்று என்று சொல்லுங்கள். "
                    "கிளாசிக் தொழில்முறை வடிவமைப்புக்கு இரண்டு என்று சொல்லுங்கள். "
                    "எளிமையான வடிவமைப்புக்கு மூன்று என்று சொல்லுங்கள். "
                    "எது உங்களுக்கு பிடிக்கும்?"
                ),
                "field": "template",
                "optional": False,
            },
            {
                "id": "name",
                "q": "What is your full name?",
                "q_ta": "உங்கள் முழு பெயர் என்ன?",
                "field": "name",
                "optional": False,
            },
            {
                "id": "email",
                "q": (
                    "What is your email address? "
                    "You can say it naturally. For example: "
                    "john dot doe at gmail dot com."
                ),
                "q_ta": (
                    "உங்கள் மின்னஞ்சல் முகவரி என்ன? "
                    "உதாரணமாக: ஜான் டாட் டோ எட் ஜிமெயில் டாட் காம்."
                ),
                "field": "email",
                "optional": True,
            },
            {
                "id": "phone",
                "q": (
                    "What is your phone number? "
                    "Just say the digits. For example: 9876543210."
                ),
                "q_ta": (
                    "உங்கள் தொலைபேசி எண் என்ன? "
                    "உதாரணமாக: 9876543210."
                ),
                "field": "phone",
                "optional": True,
            },
            {
                "id": "linkedin",
                "q": (
                    "Do you have a LinkedIn profile URL? "
                    "You can spell it out or say your LinkedIn username. "
                    "For example: linkedin dot com slash in slash john-doe. "
                    "Or say skip to continue."
                ),
                "q_ta": (
                    "உங்களுக்கு லிங்க்டின் கணக்கு இருக்கிறதா? "
                    "உங்கள் லிங்க்டின் பயனர் பெயரை சொல்லலாம். "
                    "தேவையில்லை என்றால் தவிர் என்று சொல்லுங்கள்."
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
                "q_ta": (
                    "உங்களுக்கு கிட்ஹப் அல்லது தனிப்பட்ட வலைத்தளம் இருக்கிறதா? "
                    "வலைத்தள முகவரி அல்லது பயனர் பெயரை சொல்லலாம். "
                    "தேவையில்லை என்றால் தவிர் என்று சொல்லுங்கள்."
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
                "q_ta": (
                    "உங்கள் தற்போதைய வேலை பதவி அல்லது நீங்கள் விண்ணப்பிக்கும் பதவி என்ன? "
                    "உதாரணமாக: மென்பொருள் பொறியாளர், தரவு அறிவியலாளர், அல்லது சந்தைப்படுத்தல் மேலாளர்."
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
                "q_ta": (
                    "உங்களைப் பற்றி இரண்டு அல்லது மூன்று வாக்கியங்களில் சொல்லுங்கள். "
                    "நீங்கள் எதில் ஆர்வமாக இருக்கிறீர்கள்? என்ன மதிப்பை நீங்கள் தருகிறீர்கள்?"
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
                "q_ta": (
                    "உங்கள் முக்கிய தொழில்நுட்ப அல்லது தொழில்முறை திறன்கள் என்ன? "
                    "ஒவ்வொன்றையும் தனித்தனியாக சொல்லுங்கள். "
                    "உதாரணமாக: பைத்தான், ரியாக்ட், இயந்திரக் கற்றல், தகவல் தொடர்பு."
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
                "q_ta": (
                    "உங்கள் சமீபத்திய பணி அனுபவத்தை விவரியுங்கள். "
                    "பதவி, நிறுவனம் பெயர் மற்றும் வருடங்களை சொல்லுங்கள். "
                    "உதாரணமாக: நான் இன்போசிச்-ல் மென்பொருள் உருவாக்குநராக 2021 முதல் 2024 வரை பணிபுரிந்தேன். "
                    "பணி அனுபவம் இல்லை என்றால் தவிர் என்று சொல்லுங்கள்."
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
                "q_ta": (
                    "உங்கள் கல்வி பற்றி சொல்லுங்கள். "
                    "என்ன பட்டம், எந்த கல்லூரி அல்லது பல்கலைக்கழகம், எப்போது பட்டம் பெற்றீர்கள்? "
                    "உதாரணமாக: ராஜலட்சுமி தொழில்நுட்பக் கல்லூரியில் கணினி அறிவியல் பி.டெக், 2024."
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
                "q_ta": (
                    "நீங்கள் செய்த ஒரு திட்டம் பற்றி சொல்லுங்கள். "
                    "திட்டத்தின் பெயர், அது என்ன செய்கிறது, பயன்படுத்திய தொழில்நுட்பங்கள் சொல்லுங்கள். "
                    "தேவையில்லை என்றால் தவிர் என்று சொல்லுங்கள்."
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
                "q_ta": (
                    "நீங்கள் சேர்க்க விரும்பும் சான்றிதழ்கள் அல்லது படிப்புகள் ஏதேனும் உள்ளதா? "
                    "தேவையில்லை என்றால் தவிர் என்று சொல்லுங்கள்."
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
                "q_ta": (
                    "வேறு ஏதேனும் சாதனைகள், பேசும் மொழிகள், தன்னார்வ பணி அல்லது பொழுதுபோக்குகள் உள்ளதா? "
                    "தேவையில்லை என்றால் தவிர் என்று சொல்லுங்கள்."
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
                "q_ta": (
                    "அருமை! எனக்கு தேவையான அனைத்து தகவல்களும் கிடைத்துவிட்டன. "
                    "இப்போது உங்கள் ரெஸ்யூம்-ஐ உருவாக்குகிறேன். ஒரு நிமிடம்..."
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
                "q_ta": (
                    "உங்கள் ரெஸ்யூம் தயார்! திரையில் பார்க்கலாம். "
                    "Export PDF பட்டனை பயன்படுத்தி பதிவிறக்கம் செய்யலாம், "
                    "அல்லது புதிதாக உருவாக்க restart என்று சொல்லுங்கள்."
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
            "language": "en",  # Default language, will be set when user chooses
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

    def get_current_question(self, sid: str) -> str:
        """Get the current question in the user's chosen language."""
        s = self.get_session(sid)
        if not s:
            return ""
        
        step = self.get_current_step(sid)
        if not step:
            return ""
        
        lang = s.get("language", "en")
        # Use Tamil question if language is Tamil and q_ta exists, otherwise use English
        if lang == "ta" and "q_ta" in step:
            return step["q_ta"]
        return step.get("q", "")

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

        # Handle language selection
        if field == "language":
            clean = text.strip().lower()
            if "two" in clean or "2" in clean or "tamil" in clean.lower():
                s["language"] = "ta"
            else:
                s["language"] = "en"
            return s

        # Handle skip for optional fields
        if step.get("optional") and self._is_skip(text):
            # Leave field as default (empty / [])
            return s

        # Field-specific handling
        if field == "template":
            s["data"]["template"] = self._parse_template(text)

        elif field == "email":
            s["data"]["email"] = self.__extract_email(text)

        elif field == "phone":
            s["data"]["phone"] = self.__extract_phone(text)

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
            # Strip common spoken filler from the start so the baseline is cleaner
            clean = re.sub(
                r"^\s*(so\s+)?(basically\s+)?i\s+(am|m|am\s+a|'?m\s+a|am\s+currently\s+a|work\s+as|am\s+working\s+as)\s+",
                "", text.strip(), flags=re.IGNORECASE,
            )
            clean = re.sub(
                r"^\s*(my|the)\s+(name\s+is|role\s+is|job(\s+title)?\s+is|position\s+is)\s+",
                "", clean, flags=re.IGNORECASE,
            )
            clean = re.sub(r"^\s*(so|well|basically|actually)[,\s]+", "", clean, flags=re.IGNORECASE)
            s["data"][field] = (clean[:1].upper() + clean[1:]) if clean else text.strip()

        return s

    # ────────── helpers ──────────

    # Spoken number word → digit mapping
    _WORD_TO_DIGIT = {
        "zero": "0", "oh": "0", "o": "0",
        "one": "1", "won": "1",
        "two": "2", "to": "2", "too": "2",
        "three": "3", "tree": "3",
        "four": "4", "for": "4", "fore": "4",
        "five": "5",
        "six": "6", "sicks": "6",
        "seven": "7",
        "eight": "8", "ate": "8",
        "nine": "9", "nein": "9",
    }

    _MULTIPLIER_WORDS = {"double": 2, "triple": 3}

    def _spoken_digits_to_numbers(self, text: str) -> str:
        """Convert spoken number words to digit characters.
        E.g. 'nine eight seven six five four three two one zero' → '9876543210'
             'double nine triple eight' → '99888'
             'plus nine one' → '+91'
        """
        words = text.lower().split()
        result = []
        i = 0
        while i < len(words):
            word = words[i]
            # Handle "plus" at the start (for country codes like +91)
            if word == "plus" and i == 0:
                result.append("+")
                i += 1
                continue
            # Handle "double"/"triple" + digit word
            if word in self._MULTIPLIER_WORDS and i + 1 < len(words):
                next_word = words[i + 1]
                if next_word in self._WORD_TO_DIGIT:
                    digit = self._WORD_TO_DIGIT[next_word]
                    result.append(digit * self._MULTIPLIER_WORDS[word])
                    i += 2
                    continue
            # Handle single digit word
            if word in self._WORD_TO_DIGIT:
                result.append(self._WORD_TO_DIGIT[word])
                i += 1
                continue
            # Keep anything else as-is
            result.append(word)
            i += 1
        return " ".join(result)

    def _normalize_spoken_text(self, text: str) -> str:
        """General pre-processor to normalize common speech-to-text artifacts."""
        t = text
        # Normalize email separators
        t = re.sub(r"\b(at the rate|at the rate of|at rate)\b", "@", t, flags=re.I)
        t = re.sub(r"\bat\b", "@", t, flags=re.I)
        t = re.sub(r"\b(dot|period|point)\b", ".", t, flags=re.I)
        t = re.sub(r"\b(underscore|under score)\b", "_", t, flags=re.I)
        t = re.sub(r"\b(hyphen|dash|minus)\b", "-", t, flags=re.I)
        t = re.sub(r"\b(hash|hashtag|number sign)\b", "#", t, flags=re.I)
        t = re.sub(r"\b(space)\b", " ", t, flags=re.I)
        return t

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
        """Handle many spoken email patterns:
        - 'john dot doe at gmail dot com'
        - 'john underscore doe at the rate gmail dot com'
        - 'john123 at yahoo dot co dot in'
        """
        t = text
        # First convert any spoken digits in the text
        t = self._spoken_digits_to_numbers(t)
        # Normalize spoken separators
        t = re.sub(r"\b(at the rate of|at the rate|at rate)\b", " @ ", t, flags=re.I)
        t = re.sub(r"\s+at\s+(gmail|yahoo|outlook|hotmail|icloud|protonmail|zoho|rediffmail|mail|live|aol)\b",
                    r" @ \1", t, flags=re.I)
        t = re.sub(r"\s+at\s+", " @ ", t, flags=re.I)
        t = re.sub(r"\b(dot|period|point)\b", ".", t, flags=re.I)
        t = re.sub(r"\b(underscore|under score)\b", "_", t, flags=re.I)
        t = re.sub(r"\b(hyphen|dash)\b", "-", t, flags=re.I)
        # Remove spaces around @ and .
        t = re.sub(r"\s*@\s*", "@", t)
        t = re.sub(r"\s*\.\s*", ".", t)
        t = re.sub(r"\s*_\s*", "_", t)
        t = re.sub(r"\s*-\s*", "-", t)
        # Remove remaining spaces within what looks like an email
        # Try to find email pattern
        match = re.search(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", t)
        if match:
            return match.group(0).lower()
        # Fallback: try removing all spaces and re-matching
        t_nospace = re.sub(r"\s+", "", t)
        match = re.search(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", t_nospace)
        return match.group(0).lower() if match else ""

    def __extract_phone(self, text: str) -> str:
        """Extract phone number, handling spoken digit words.
        E.g. 'nine eight seven six five four three two one zero' → '9876543210'
             'my number is double nine double eight seven six five four three two' → '9988765432'
             '+91 9876543210' → '+919876543210'
        """
        # First convert spoken digit words to actual digits
        t = self._spoken_digits_to_numbers(text)
        # Now extract digits (and leading +)
        digits = re.sub(r"[^\d+]", "", t)
        if len(re.sub(r"[^\d]", "", digits)) >= 7:
            return digits
        # Fallback: try original text
        digits = re.sub(r"[^\d+]", "", text)
        if len(re.sub(r"[^\d]", "", digits)) >= 7:
            return digits
        match = re.search(r"[\d\s\-().+]{7,}", text)
        if match:
            phone = match.group(0).strip()
            return phone if len(phone) >= 7 else ""
        return ""
