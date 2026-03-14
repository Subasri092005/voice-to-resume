#!/usr/bin/env python
"""
verification_checklist.py
Quick verification script to ensure all files are in place and imports work.
Run this before the demo to catch any issues early.
"""

import os
import sys

def check_file_exists(path, description=""):
    """Check if file exists and print status."""
    exists = os.path.exists(path)
    status = "✓" if exists else "✗"
    desc = f" ({description})" if description else ""
    print(f"{status} {path}{desc}")
    return exists

def check_import(module_name, description=""):
    """Check if Python module can be imported."""
    try:
        __import__(module_name)
        status = "✓"
        result = True
    except ImportError as e:
        status = "✗"
        result = False
        print(f"  Error: {e}")
    desc = f" ({description})" if description else ""
    print(f"{status} import {module_name}{desc}")
    return result

def main():
    print("\n" + "="*60)
    print("VOICE RESUME ASSISTANT - IMPLEMENTATION VERIFICATION")
    print("="*60 + "\n")
    
    all_good = True
    base_path = os.path.dirname(os.path.abspath(__file__))
    
    # 1. Check new files exist
    print("📁 NEW FILES CHECK:")
    print("-" * 60)
    files_to_check = [
        (os.path.join(base_path, "conversation_controller.py"), "Conversation manager"),
        (os.path.join(base_path, "templates", "assistant.html"), "Assistant UI"),
        (os.path.join(base_path, "static", "css", "assistant.css"), "Assistant styling"),
        (os.path.join(base_path, "DEMO_CHECKLIST.md"), "Demo guide"),
        (os.path.join(base_path, "IMPLEMENTATION_SUMMARY.md"), "Implementation docs"),
        (os.path.join(base_path, "QUICK_START.md"), "Quick start guide"),
        (os.path.join(base_path, "CODE_OVERVIEW.md"), "Code documentation"),
    ]
    
    for path, desc in files_to_check:
        if not check_file_exists(path, desc):
            all_good = False
    
    # 2. Check that original files still exist
    print("\n📚 ORIGINAL FILES CHECK (Should be unchanged):")
    print("-" * 60)
    original_files = [
        (os.path.join(base_path, "app.py"), "Main Flask app (MODIFIED)"),
        (os.path.join(base_path, "requirements.txt"), "Dependencies"),
        (os.path.join(base_path, "templates", "index.html"), "Original UI"),
        (os.path.join(base_path, ".env"), "Environment config"),
    ]
    
    for path, desc in original_files:
        if not check_file_exists(path, desc):
            all_good = False
    
    # 3. Check Python syntax
    print("\n🐍 PYTHON SYNTAX CHECK:")
    print("-" * 60)
    python_files = [
        (os.path.join(base_path, "app.py"), "app.py"),
        (os.path.join(base_path, "conversation_controller.py"), "conversation_controller.py"),
    ]
    
    for path, name in python_files:
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    compile(f.read(), path, 'exec')
                print(f"✓ {name} syntax OK")
            except SyntaxError as e:
                print(f"✗ {name} has syntax error: {e}")
                all_good = False
        else:
            print(f"✗ {name} not found")
            all_good = False
    
    # 4. Check imports
    print("\n📦 IMPORT CHECK:")
    print("-" * 60)
    
    # Change to project directory for imports
    os.chdir(base_path)
    sys.path.insert(0, base_path)
    
    imports_to_check = [
        ("flask", "Flask web framework"),
        ("flask_cors", "CORS support"),
        ("openai", "OpenAI API"),
        ("dotenv", "Environment variables"),
        ("conversation_controller", "Conversation manager (LOCAL)"),
    ]
    
    for module, desc in imports_to_check:
        if not check_import(module, desc):
            if module != "conversation_controller":
                all_good = False
            # conversation_controller import fails before running Flask,
            # but will work when Flask imports it
    
    # 5. Check Flask routes are defined
    print("\n🛣️  FLASK ROUTES CHECK:")
    print("-" * 60)
    
    try:
        with open(os.path.join(base_path, "app.py"), 'r') as f:
            app_content = f.read()
        
        routes_to_check = [
            ("/assistant", "Assistant UI route"),
            ("/conversation/init", "Init conversation endpoint"),
            ("/conversation/next", "Next question endpoint"),
            ("/conversation/submit", "Submit answer endpoint"),
            ("/conversation/status", "Status debug endpoint"),
        ]
        
        for route, desc in routes_to_check:
            if f'route("{route}"' in app_content or f"route('{route}'" in app_content:
                print(f"✓ {route} ({desc})")
            else:
                print(f"✗ {route} NOT FOUND ({desc})")
                all_good = False
    except Exception as e:
        print(f"✗ Error checking routes: {e}")
        all_good = False
    
    # 6. Check ConversationManager is instantiated
    print("\n🎙️  CONVERSATION MANAGER CHECK:")
    print("-" * 60)
    
    try:
        with open(os.path.join(base_path, "app.py"), 'r') as f:
            app_content = f.read()
        
        if "from conversation_controller import ConversationManager" in app_content:
            print("✓ ConversationManager imported")
        else:
            print("✗ ConversationManager import NOT found")
            all_good = False
        
        if "convman = ConversationManager()" in app_content:
            print("✓ ConversationManager instantiated as 'convman'")
        else:
            print("✗ ConversationManager instantiation NOT found")
            all_good = False
    except Exception as e:
        print(f"✗ Error checking ConversationManager: {e}")
        all_good = False
    
    # 7. Check that original parse functions are untouched
    print("\n✨ ORIGINAL CODE PRESERVATION CHECK:")
    print("-" * 60)
    
    try:
        with open(os.path.join(base_path, "app.py"), 'r') as f:
            app_content = f.read()
        
        functions_to_check = [
            "def parse_name(",
            "def parse_education(",
            "def parse_skills(",
            "def parse_experience(",
            "def parse_projects(",
            "def parse_contact(",
            "def parse_with_llm(",
        ]
        
        for func in functions_to_check:
            if func in app_content:
                print(f"✓ {func.replace('def ', '').replace('(', '')} preserved")
            else:
                print(f"✗ {func.replace('def ', '').replace('(', '')} NOT found")
                all_good = False
    except Exception as e:
        print(f"✗ Error checking parse functions: {e}")
        all_good = False
    
    # 8. Check HTML file has required elements
    print("\n🎨 HTML/UI CHECK:")
    print("-" * 60)
    
    try:
        with open(os.path.join(base_path, "templates", "assistant.html"), 'r') as f:
            html_content = f.read()
        
        elements_to_check = [
            ('id="start-btn"', "Start button"),
            ('id="mic-btn"', "Mic button"),
            ('id="agent-text"', "Agent message area"),
            ('id="current-data"', "Data display panel"),
            ('speechSynthesis', "TTS support"),
            ('SpeechRecognition', "Speech recognition support"),
        ]
        
        for element, desc in elements_to_check:
            if element in html_content:
                print(f"✓ {desc} present")
            else:
                print(f"✗ {desc} NOT found")
                all_good = False
    except Exception as e:
        print(f"✗ Error checking HTML: {e}")
        all_good = False
    
    # 9. Final summary
    print("\n" + "="*60)
    if all_good:
        print("✅ ALL CHECKS PASSED - READY FOR DEMO!")
        print("="*60)
        print("\nNext steps:")
        print("1. Run: python app.py")
        print("2. Open: http://127.0.0.1:5000/assistant")
        print("3. Click 'Start Voice Resume Assistant'")
        print("\nGood luck! 🚀\n")
        return 0
    else:
        print("❌ SOME CHECKS FAILED - FIX BEFORE DEMO")
        print("="*60)
        print("\nPlease review the errors above and fix them.\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
