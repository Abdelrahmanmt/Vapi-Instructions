from flask import Flask, request, jsonify
import threading
import time
import requests

@app.route('/')
def home():
    return "Hello from Flask!"

app = Flask(__name__)

# Your VAPI API details
VAPI_API_BASE = "https://api.vapi.ai"  # Corrected base URL
VAPI_API_KEY = "your_api_key_here"

CALL_DURATION_LIMIT = 80       # seconds
END_MESSAGE_DURATION = 10      # seconds

# Simple storage for active calls and timers
active_calls = {}

def play_end_message(call_id):
    print(f"Playing end message on call {call_id}")
    url = f"{VAPI_API_BASE}/call/{call_id}/play"  # Corrected endpoint path
    payload = {
        "type": "tts",
        "text": "Your call will end shortly."
    }
    headers = {"Authorization": f"Bearer {VAPI_API_KEY}"}
    response = requests.post(url, json=payload, headers=headers)
    if response.ok:
        print(f"End message started for call {call_id}")
    else:
        print(f"Failed to play end message: {response.text}")

def hangup_call(call_id):
    print(f"Hanging up call {call_id}")
    url = f"{VAPI_API_BASE}/call/{call_id}/hangup"  # Corrected endpoint path
    headers = {"Authorization": f"Bearer {VAPI_API_KEY}"}
    response = requests.post(url, headers=headers)
    if response.ok:
        print(f"Call {call_id} hung up successfully")
    else:
        print(f"Failed to hang up call: {response.text}")



def schedule_end_sequence(call_id):
    # Wait (call limit - message duration)
    time.sleep(CALL_DURATION_LIMIT - END_MESSAGE_DURATION)
    
    # Double-check call is still active
    if call_id in active_calls:
        play_end_message(call_id)
        
        # Wait message duration
        time.sleep(END_MESSAGE_DURATION)
        
        # Hang up call
        if call_id in active_calls:
            hangup_call(call_id)
            active_calls.pop(call_id, None)

@app.route('/webhook/call-start', methods=['POST'])
def call_start():
    data = request.json
    call_id = data.get('call_id')
    if not call_id:
        return jsonify({"error": "Missing call_id"}), 400
    
    print(f"Call started: {call_id}")
    active_calls[call_id] = True
    
    # Start background thread to handle end message + hangup
    thread = threading.Thread(target=schedule_end_sequence, args=(call_id,))
    thread.start()
    
    return jsonify({"status": "call timer started"}), 200

@app.route('/webhook/call-end', methods=['POST'])
def call_end():
    data = request.json
    call_id = data.get('call_id')
    if call_id in active_calls:
        active_calls.pop(call_id)
        print(f"Call ended: {call_id}, cleaned up.")
    return jsonify({"status": "call ended"}), 200

if __name__ == '__main__':
    app.run(port=5000)
