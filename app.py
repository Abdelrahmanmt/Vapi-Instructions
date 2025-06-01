import os
from flask import Flask, request, jsonify
import time
import requests
import threading

app = Flask(__name__)

# Store your secret token (make up any secure random string)
# Read secret from environment variable
WEBHOOK_SECRET = os.environ.get('WEBHOOK_SECRET')

# Store call start times
call_timers = {}

@app.route('/')
def home():
    # Basic check to see if secret is loaded (optional, for initial debugging)
    if not WEBHOOK_SECRET:
        return "Vapi Webhook Server is running, but WEBHOOK_SECRET is not set!", 500
    return "Vapi Webhook Server is running!"

def verify_signature(request):
    """Verify the request is coming from Vapi"""
    if not WEBHOOK_SECRET:
        print("WEBHOOK_SECRET environment variable not set!")
        return False

    signature = request.headers.get('X-Vapi-Secret')
    if signature != WEBHOOK_SECRET:
        print(f"Signature mismatch! Received: '{signature}', Expected: '{WEBHOOK_SECRET}'")
        return False
    return True

def end_call_after_timeout(call_id, control_url):
    """Function to wait and then end the call after timeout"""
    print(f"[Timer] Starting 35-second timer for call {call_id}")
    time.sleep(35)  # Wait 35 seconds

    final_message = {
        "type": "say",
        "content": "Thank you for trying our demo agent. Your session has now ended. When you're ready, please use the booking section here on this page to schedule a consultation with one of our experts. We look forward to assisting you soon. Have a great day!",
        "endCallAfterSpoken": True
    }

    try:
        print(f"[Timer] Sending final message and ending call {call_id}")
        response = requests.post(control_url, json=final_message)
        print(f"[Timer] End call response status: {response.status_code}")
    except Exception as e:
        print(f"[Timer] Error ending call: {e}")

@app.route('/server', methods=['POST'])
def handle_call_events():
    if not verify_signature(request):
        print("[Webhook] Signature verification failed!")
        return jsonify({"error": "Invalid signature"}), 401

    data = request.json

    message_data = data.get('message', {})
    call_id = message_data.get('call', {}).get('id')
    message_type = message_data.get('type')

    print(f"[Webhook] Received message type: {message_type}, call_id: {call_id}")

    if message_type == 'status-update':
        status = message_data.get('status')
        print(f"[Webhook] Call status update for {call_id}: {status}")

        if status == 'in-progress' and call_id:
            if call_id not in call_timers:
                call_timers[call_id] = time.time()
                control_url = message_data.get('call', {}).get('monitor', {}).get('controlUrl')

                if control_url:
                    print(f"[Webhook] Starting timer thread for call {call_id}")
                    timer_thread = threading.Thread(
                        target=end_call_after_timeout,
                        args=(call_id, control_url)
                    )
                    timer_thread.daemon = True
                    timer_thread.start()
                else:
                    print(f"[Webhook] No control URL found for call {call_id}")
            else:
                print(f"[Webhook] Timer already started for call {call_id}")
    else:
        print(f"[Webhook] Ignored message type: {message_type}")

    return jsonify({"status": "ok"}), 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
