# 📚 CODE OVERVIEW & ARCHITECTURE

## File Structure

```
voice-to-resume/
├── app.py                          ← MODIFIED: +100 lines
├── conversation_controller.py      ← NEW: 120 lines
├── requirements.txt                (unchanged)
├── README.md                       (original)
├── templates/
│   ├── index.html                 (original)
│   └── assistant.html             ← NEW: 160 lines (UI + inline JS)
├── static/
│   ├── css/
│   │   └── assistant.css          ← NEW: 60 lines
│   └── assets/
│       ├── script.js              (original, unused in assistant)
│       └── styles.css             (original, unused in assistant)
├── DEMO_CHECKLIST.md              ← NEW: Demo guide
├── IMPLEMENTATION_SUMMARY.md      ← NEW: Technical summary
├── QUICK_START.md                 ← NEW: Quick reference
└── test_endpoints.py              ← NEW: Optional endpoint tester
```

---

## 1️⃣ conversation_controller.py

**Purpose**: Session and conversation flow management

**Key Class: ConversationManager**

```python
class ConversationManager:
    def __init__(self):
        self.sessions = {}  # Dict[session_id, session_data]
        self.flow = [...]   # List of 10 step definitions
    
    def create_session() → session_dict
    def get_session(sid) → session_dict or None
    def get_current_step(sid) → step_dict
    def advance(sid) → None (moves to next step)
    def submit_answer(sid, text) → None (stores answer)
```

**Flow Definition** (10 steps):
```python
[
    {"id": "greeting", "q": "Hello!...", "field": None},
    {"id": "name", "q": "What's your full name?", "field": "name"},
    {"id": "job_role", "q": "What's your job role?", "field": "job_role"},
    {"id": "experience", "q": "How many years?", "field": "experience"},
    {"id": "work_history", "q": "Describe your job", "field": "work_history"},
    {"id": "skills", "q": "Tell me your skills", "field": "skills"},
    {"id": "template", "q": "Choose template", "field": "template"},
    {"id": "color", "q": "Choose color", "field": "color"},
    {"id": "confirmation", "q": "Shall I proceed?", "field": None},
    {"id": "done", "q": "Your resume is ready!", "field": None}
]
```

**Session Data Structure**:
```python
{
    "session_id": "uuid-string",
    "current_index": 0,
    "data": {
        "name": "",
        "job_role": "",
        "experience": "",
        "work_history": "",
        "skills": [],
        "template": "",
        "color": ""
    },
    "completed": False
}
```

**Smart Field Handling**:
- `skills`: Splits on "and" / comma, deduplicates, title-cases
- `template`: Checks if "classic" or "modern" in text (case-insensitive)
- `name`, `job_role`, etc.: Stored as raw text for post-processing by Flask

---

## 2️⃣ app.py Modifications

**Changes Made** (4 locations):

### Location 1: Imports (Line 10)
```python
from conversation_controller import ConversationManager
```

### Location 2: Manager Initialization (Line ~15)
```python
convman = ConversationManager()
```

### Location 3: New Route (Line ~435)
```python
@app.route("/assistant")
def assistant():
    return render_template("assistant.html")
```

### Location 4: New Endpoints (Line ~500-590)

#### Endpoint: GET /conversation/init
```python
@app.route("/conversation/init", methods=["GET"])
def conversation_init():
    session = convman.create_session()
    step = convman.get_current_step(session["session_id"])
    return jsonify({
        "session_id": session["session_id"],
        "step_id": step["id"],
        "question": step["q"],
        "data": session["data"]
    })
```
**Response**:
```json
{
  "session_id": "12345-abcd-...",
  "step_id": "greeting",
  "question": "Hello! I am your voice resume assistant...",
  "data": {"name": "", "job_role": "", ...}
}
```

#### Endpoint: POST /conversation/submit
```python
@app.route("/conversation/submit", methods=["POST"])
def conversation_submit():
    payload = request.get_json()
    sid = payload["session_id"]
    text = payload["text"]
    
    # Store raw answer
    convman.submit_answer(sid, text)
    
    # Post-process with existing parse_* functions
    if field == "name":
        parsed = parse_name(text)
        session["data"]["name"] = parsed
    elif field == "skills":
        parsed = parse_skills(text)
        session["data"]["skills"] = parsed
    
    # Advance and return next question
    convman.advance(sid)
    next_step = convman.get_current_step(sid)
    return jsonify({
        "step_id": next_step["id"],
        "question": next_step["q"],
        "data": session["data"],
        "completed": session["completed"]
    })
```

**Request Body**:
```json
{
  "session_id": "12345-abcd-...",
  "text": "My name is Rahul Kumar"
}
```

**Response**:
```json
{
  "session_id": "12345-abcd-...",
  "step_id": "job_role",
  "question": "What is your job role...",
  "data": {"name": "Rahul Kumar", ...},
  "completed": false
}
```

#### Endpoint: GET /conversation/next
```python
# Fetch next question without submitting
# Used if user says "repeat" or "skip"
```

#### Endpoint: GET /conversation/status
```python
# Debug endpoint: returns full session state
# Useful for testing
```

**Integration with Existing Parsers**:
- Uses `parse_name(text)` from original code ✅
- Uses `parse_skills(text)` from original code ✅
- Does NOT modify `/parse` endpoint ✅
- Does NOT modify existing resume logic ✅

---

## 3️⃣ templates/assistant.html

**Structure**:
- `<main>` with role="main"
- One card container
- Title, agent message area, controls, status, data viewer

**Key Elements**:

```html
<div id="agent-area" aria-live="polite">
  <p id="agent-text">Press start to begin.</p>
</div>

<button id="start-btn" class="primary">
  Start Voice Resume Assistant
</button>

<button id="mic-btn" class="mic" disabled>
  🎤 Start Listening
</button>

<div id="listening-indicator" class="waveform"></div>

<pre id="current-data" aria-live="polite">{}</pre>
```

**Accessibility Features**:
- `aria-live="polite"` → Screen reader announces updates
- `aria-label` on buttons → Clear button purpose
- High contrast: dark text on light background
- Large font: 18px+ for agent text
- No mouse-only interactions: all buttons keyboard/voice compatible

**JavaScript Flow**:

```javascript
// 1. User clicks "Start"
startBtn.addEventListener('click', initConversation)
  → fetch('/conversation/init')
  → speak(question)  // Browser TTS
  → enable mic button

// 2. User clicks "Mic" or says voice
micBtn.addEventListener('click', startRecognition)
  → recognizer.start()  // Web Speech API
  → wait for result

// 3. Browser recognizes speech
recognizer.onresult
  → POST '/conversation/submit' with transcript
  → receive next question
  → speak(next_question)
  → update data view
  → if not completed, loop to step 2

// 4. Conversation ends
convman.session.completed = true
  → agent says "Your resume is ready!"
```

**Browser APIs Used**:
1. `speechSynthesis` (speaker)
   - Standard API, ~95% browser support
   - Works: Chrome, Edge, Safari, Firefox
   ```javascript
   speak(text) {
     const msg = new SpeechSynthesisUtterance(text);
     window.speechSynthesis.speak(msg);
   }
   ```

2. `SpeechRecognition` / `webkitSpeechRecognition` (microphone)
   - Best: Chrome, Edge
   - Fallback: Prompt for text input
   ```javascript
   recognizer = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
   recognizer.onresult = (event) => {
     const transcript = event.results[0][0].transcript;
     submitAnswer(transcript);
   };
   ```

---

## 4️⃣ static/css/assistant.css

**Design System**:
```css
:root {
  --bg1: linear-gradient(135deg, #2abfac, #6c5ce7);  /* Teal → Purple */
  --card-bg: rgba(255, 255, 255, 0.96);              /* White card */
  --accent: #6c5ce7;                                 /* Purple */
  --text: #111;                                      /* Dark gray */
}
```

**Layout**:
- Centered card on gradient background
- Max-width: 880px (readable on mobile too)
- Padding: 28px (generous whitespace)

**Animations**:
```css
.waveform.listening {
  animation: pulse 1s infinite;  /* Breathing effect */
}
```

**Responsive**:
- Flexbox for controls
- No breakpoints needed for demo (works on all sizes)

---

## 5️⃣ Data Flow Diagram

```
┌─────────────────────┐
│  /assistant page    │
│  (templates/       │
│   assistant.html)  │
└──────────┬──────────┘
           │
           │ GET /conversation/init
           ↓
┌──────────────────────────┐
│  Flask Backend (app.py)  │
│  ConversationManager     │
│                          │
│  - Create session        │
│  - Return step[0]        │
└──────────┬───────────────┘
           │
           │ {session_id, question, data}
           ↓
   Agent speaks question (TTS)
           │
   User speaks answer (Web Speech API)
           │
           │ POST /conversation/submit
           │ {session_id, text}
           ↓
┌──────────────────────────┐
│  Flask Backend           │
│                          │
│  1. Store answer         │
│  2. Run parse_name() or  │
│     parse_skills()       │
│  3. Advance flow         │
│  4. Get next step        │
└──────────┬───────────────┘
           │
           │ {step_id, question, data, completed}
           ↓
   Agent speaks confirmation with name
   ("Great, [name]! What's next?")
           │
           ↓ [Loop or finish]
```

---

## 6️⃣ Integration with Existing Code

**What Was Preserved** (✅ No changes):

1. **Parse Functions**:
   - `parse_name(text)` — Still in app.py, called during `/conversation/submit`
   - `parse_skills(text)` — Still in app.py, called during `/conversation/submit`
   - `parse_education()`, `parse_experience()` — Available for future use
   - All regex patterns and helper functions — Untouched

2. **Existing Endpoints**:
   - `GET /` — Still serves old index.html
   - `POST /parse` — Still available for field parsing
   - `POST /transcribe` — Still available for Whisper

3. **Resume Generation**:
   - Jinja2 templates — Ready to receive session data
   - PDF export — Can be called with session data

4. **Environment Setup**:
   - `.env` file — OpenAI key still loaded
   - `requirements.txt` — No new dependencies added

**What's New** (✨ Phase 2):

- Conversation flow management (conversation_controller.py)
- Voice agent endpoints (4 new routes in app.py)
- Modern UI page (templates/assistant.html)
- Styling (static/css/assistant.css)

**How They Connect**:
- Phase 1 code: Parsing & PDF generation
- Phase 2 code: Conversation & voice I/O
- **Future Phase 3**: Connect session data to resume preview + PDF

---

## 7️⃣ Example Session Lifecycle

```
Time 00:00 - User lands on /assistant
  ├─ Frontend: Shows "Press start to begin"

Time 00:05 - User clicks "Start"
  ├─ Frontend: fetch('/conversation/init')
  ├─ Backend: Create session {'session_id': 'abc123', 'current_index': 0, ...}
  ├─ Backend: Return step[0] (greeting)
  ├─ Frontend: Agent speaks "Hello! I am your..."
  └─ Frontend: Enable "🎤 Start Listening" button

Time 00:10 - User clicks "Start Listening" and speaks "My name is Rahul Kumar"
  ├─ Frontend: Web Speech API captures transcript
  ├─ Frontend: fetch('/conversation/submit', {session_id, text: "..."})
  ├─ Backend: convman.submit_answer(sid, "My name is Rahul Kumar")
  ├─ Backend: Call parse_name("My name is Rahul Kumar") → "Rahul Kumar"
  ├─ Backend: session['data']['name'] = "Rahul Kumar"
  ├─ Backend: convman.advance(sid) → current_index = 1
  ├─ Backend: next_step = step[1] (job_role)
  ├─ Backend: Return {step_id: 'job_role', question: 'What is...', data: {...}}
  ├─ Frontend: Agent speaks "Great Rahul Kumar! What is your job role?"
  └─ Frontend: Update JSON panel to show {"name": "Rahul Kumar", ...}

Time 00:20 - User says "I'm a web developer"
  ├─ Backend: Store, advance, return next question
  ├─ Agent: "How many years of experience?"
  └─ [Loop continues...]

Time 02:00 - User says "Yes" to confirmation
  ├─ Backend: advance → completed = True
  ├─ Agent: "Your resume preview is ready!"
  └─ Frontend: Shows final JSON with all collected data
```

---

## 8️⃣ Testing the Implementation

**Manual Tests**:

1. **Import Test**:
   ```bash
   python -c "import app; import conversation_controller"
   # Should succeed with no errors
   ```

2. **Syntax Check**:
   ```bash
   python -m py_compile app.py conversation_controller.py
   # Should succeed
   ```

3. **Endpoint Test** (after starting server):
   ```bash
   curl http://127.0.0.1:5000/conversation/init
   # Should return JSON with session_id, step_id, question
   ```

4. **UI Test**:
   ```
   http://127.0.0.1:5000/assistant
   - Click "Start Voice Resume Assistant"
   - Should hear agent speak greeting
   - Click "Start Listening" and speak
   - Should advance and hear next question
   ```

---

## 9️⃣ Customization Points (For Future)

If you want to extend this later:

1. **Change conversation flow**:
   ```python
   # In conversation_controller.py, modify self.flow list
   self.flow = [
       {"id": "custom_step", "q": "Your question", "field": "field_name"},
       ...
   ]
   ```

2. **Add field processing**:
   ```python
   # In app.py /conversation/submit endpoint
   elif step_field == "new_field":
       parsed = parse_new_field(text)
       session["data"]["new_field"] = parsed
   ```

3. **Change styling**:
   ```css
   /* In static/css/assistant.css, update CSS variables */
   --bg1: linear-gradient(135deg, #newcolor1, #newcolor2);
   ```

4. **Modify agent voice**:
   ```javascript
   // In templates/assistant.html, update speak() function
   msg.rate = 0.8;  // Slower
   msg.pitch = 1.2; // Higher
   ```

5. **Add voice commands** (e.g., "repeat"):
   ```javascript
   // In recognizer.onresult handler
   if (text.toLowerCase().includes("repeat")) {
     agentText.textContent = currentQuestion;
     speak(currentQuestion);
   }
   ```

---

## 🔟 Deployment Notes

**Development** (Current):
- In-memory sessions (lost on server restart)
- Single process (no load balancing)
- Debug off (`debug=False`)

**For Production** (Future):
- Use Flask sessions with secure cookie storage
- Or use a database (PostgreSQL, MongoDB) for persistence
- Use a WSGI server (Gunicorn, uWSGI) instead of Flask dev server
- Add HTTPS (required for Web Speech API on production)
- Add rate limiting and input validation
- Add logging to CloudWatch/Datadog

**For This Demo**:
- Everything works as-is ✅
- No production changes needed ✅
- Focus on user experience ✅

---

## Summary Table

| Component | Type | Lines | Purpose |
|-----------|------|-------|---------|
| conversation_controller.py | Python | 120 | Session management + flow |
| app.py (modifications) | Python | +100 | Endpoints + manager integration |
| assistant.html | HTML/CSS/JS | 160 | UI + voice I/O |
| assistant.css | CSS | 60 | Styling |
| DEMO_CHECKLIST.md | Markdown | 250 | Demo guide |
| IMPLEMENTATION_SUMMARY.md | Markdown | 200 | Technical summary |
| QUICK_START.md | Markdown | 150 | Quick reference |
| **TOTAL** | | **~1040** | **Complete system** |

---

**All systems are go for tomorrow's review! 🚀**
