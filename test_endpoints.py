#!/usr/bin/env python
import urllib.request
import json

# Test /conversation/init
try:
    response = urllib.request.urlopen('http://127.0.0.1:5000/conversation/init')
    data = json.loads(response.read())
    print("✓ /conversation/init endpoint works!")
    print(f"  - Session ID: {data['session_id'][:12]}...")
    print(f"  - Step ID: {data['step_id']}")
    print(f"  - Question: {data['question'][:60]}...")
    print()
    
    # Extract session ID for next test
    session_id = data['session_id']
    
    # Test /conversation/submit
    print("✓ Testing /conversation/submit...")
    submit_data = json.dumps({
        "session_id": session_id,
        "text": "My name is Rahul Kumar"
    }).encode('utf-8')
    
    req = urllib.request.Request(
        'http://127.0.0.1:5000/conversation/submit',
        data=submit_data,
        headers={'Content-Type': 'application/json'}
    )
    response = urllib.request.urlopen(req)
    result = json.loads(response.read())
    print(f"  - Next Step: {result['step_id']}")
    print(f"  - Next Question: {result['question'][:60]}...")
    print(f"  - Data collected: name = '{result['data']['name']}'")
    print()
    print("✓ All endpoints working correctly!")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
