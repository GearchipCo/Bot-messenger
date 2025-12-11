from flask import Flask, request, jsonify
import requests
import os
from openai import OpenAI

app = Flask(__name__)

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

def send_message(recipient_id, text):
    url = f"https://graph.facebook.com/v18.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    data = {
        "recipient": {"id": recipient_id},
        "message": {"text": text}
    }
    response = requests.post(url, json=data)
    print("FB response:", response.text)

@app.route("/", methods=["GET"])
def home():
    return "Bot funcionando", 200

@app.route("/webhook", methods=["GET"])
def verify():
    if request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge")
    return "Error de verificación", 403

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("Mensaje recibido:", data)

    if "entry" in data:
        for entry in data["entry"]:
            messaging = entry.get("messaging")
            if messaging:
                for message in messaging:
                    sender_id = message["sender"]["id"]
                    if "text" in message.get("message", {}):
                        text = message["message"]["text"]

                        # Respuesta con OpenAI
                        completion = client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=[{"role": "user", "content": text}]
                        )

                        reply = completion.choices[0].message.content
                        send_message(sender_id, reply)

    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
