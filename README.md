## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/subasri092005/voice-to-resume.git
cd voice-to-resume
```

### 2. Create Virtual Environment

```bash
python -m venv venv
```

Activate environment

Windows:

```bash
venv\Scripts\activate
```

Mac/Linux:

```bash
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file:

```
GROQ_API_KEY=your_api_key_here
```

### 5. Run the Application

```bash
python app.py
```

### 6. Open Browser

```
http://localhost:5000
```

---

## Project Description

This application collects user information through a voice-based conversation and automatically generates structured resume content using AI.
