import requests
from flask import Flask, request

app = Flask(__name__)

# === CONFIGURACIÓN ===
VERIFY_TOKEN = "3431172002" 
PAGE_ACCESS_TOKEN = "EAALRZBMCczSoBQCmb5uPF57wart9Orhf8xUwXiIShpfusmkMqOuwnTZC7ZAwH3EBF44utiSZBA5eeq6JX9qOQn54BtR1cwJEdko4GdarhcfhJ3bYefaibWRFLC5P655cUJNpPvKgCuZBZCCQTmZC7ZAPNtsrBvJnOV24y9SHmfogGNzs4or5ZA0kHvNnx5GMVfq0yw2gQFAZDZD"  # cambia esto

FB_API_URL = "https://graph.facebook.com/v17.0/me/messages"


# === WEBHOOK ===
@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')

        if mode == "subscribe" and token == VERIFY_TOKEN:
            return challenge, 200
        else:
            return "Token inválido", 403

    if request.method == 'POST':
        data = request.json

        print("Evento recibido:", data)

        if "entry" in data:
            for entry in data["entry"]:
                if "messaging" in entry:
                    for event in entry["messaging"]:
                        if "message" in event:  # Mensaje normal
                            sender_id = event["sender"]["id"]
                            message_text = event["message"].get("text", "")

                            enviar_mensaje(sender_id, f"Recibí tu mensaje: {message_text}")

                        elif "postback" in event:  # Botón Get Started
                            sender_id = event["sender"]["id"]
                            enviar_mensaje(sender_id, "¡Hola! ¿En qué puedo ayudarte?")

        return "EVENT_RECEIVED", 200


# === FUNCIÓN PARA RESPONDER ===
def enviar_mensaje(recipient_id, text):
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text}
    }

    params = {"access_token": PAGE_ACCESS_TOKEN}

    response = requests.post(FB_API_URL, params=params, json=payload)

    print("Respuesta envío:", response.text)


@app.route('/')
def home():
    return "Bot funcionando correctamente", 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
