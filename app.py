import os
import requests
from flask import Flask, request
from openai import OpenAI

app = Flask(__name__)

VERIFY_TOKEN = "3431172002"  # usa el que pusiste en Meta

# Cargar claves desde las variables del servidor
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

def send_message(recipient_id, text):
    url = "https://graph.facebook.com/v17.0/me/messages"
    params = {"access_token": PAGE_ACCESS_TOKEN}
    data = {
        "recipient": {"id": recipient_id},
        "message": {"text": text}
    }
    requests.post(url, params=params, json=data)


def ai_response(user_message):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Eres un asistente útil y amable."},
                {"role": "user", "content": user_message}
            ],
            max_tokens=300
        )
        return response.choices[0].message.content
    except Exception as e:
        print("Error con OpenAI:", e)
        return "Hubo un error procesando tu mensaje."


@app.route('/webhook', methods=['GET'])
def verify():
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    if token == VERIFY_TOKEN:
        return challenge
    return "Token inválido", 403


@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()

    if "entry" in data:
        for entry in data["entry"]:
            for event in entry.get("messaging", []):
                sender = event["sender"]["id"]

                if "message" in event and "text" in event["message"]:
                    text = event["message"]["text"]

                    # Obtener respuesta IA
                    reply = ai_response(text)

                    # Enviar respuesta
                    send_message(sender, reply)

    return "ok", 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
