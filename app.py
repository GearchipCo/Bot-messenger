from flask import Flask, request, jsonify
import requests
import os
import json
import logging
from openai import OpenAI

# ===============================
# Configuración inicial
# ===============================
app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ===============================
# Debug inicial
# ===============================
print("=" * 60)
print("DEBUG INICIAL")
print(f"VERIFY_TOKEN existe: {bool(VERIFY_TOKEN)}")
print(f"PAGE_ACCESS_TOKEN existe: {bool(PAGE_ACCESS_TOKEN)}")
print(f"OPENAI_API_KEY existe: {bool(OPENAI_API_KEY)}")
print("=" * 60)

# ===============================
# Cliente OpenAI
# ===============================
client = OpenAI(api_key=OPENAI_API_KEY)

# ===============================
# Cargar conocimientos (JSON)
# ===============================
try:
    with open("conocimientos.json", "r", encoding="utf-8") as f:
        CONOCIMIENTOS = json.load(f)

    SYSTEM_CONTEXT = f"""
Eres un asistente oficial del Instituto Tecnológico Superior del Oriente del Estado de Hidalgo (ITESA).

Responde únicamente con base en la información oficial proporcionada.
Si la información no está disponible, indícalo de forma clara y amable.

No inventes datos.
Responde de forma clara, breve y profesional.

Información oficial:
{json.dumps(CONOCIMIENTOS, ensure_ascii=False, indent=2)}
"""
    print("✅ conocimientos.json cargado correctamente")

except Exception as e:
    SYSTEM_CONTEXT = "Eres un asistente educativo."
    print("❌ Error cargando conocimientos.json:", str(e))

# ===============================
# Enviar mensaje a Facebook
# ===============================
def send_message(recipient_id, text):
    print("\n" + "=" * 60)
    print("DEBUG send_message")
    print(f"Recipient ID: {recipient_id}")
    print(f"Mensaje: {text}")

    if not PAGE_ACCESS_TOKEN:
        print("❌ PAGE_ACCESS_TOKEN vacío")
        return

    url = f"https://graph.facebook.com/v18.0/me/messages"
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text}
    }
    params = {"access_token": PAGE_ACCESS_TOKEN}

    try:
        response = requests.post(url, params=params, json=payload, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Respuesta FB: {response.text}")
    except Exception as e:
        print("❌ Error enviando mensaje:", str(e))

    print("=" * 60 + "\n")

# ===============================
# Rutas
# ===============================
@app.route("/", methods=["GET"])
def home():
    return "Bot ITESA activo", 200

@app.route("/debug", methods=["GET"])
def debug():
    return jsonify({
        "server": "running",
        "verify_token": bool(VERIFY_TOKEN),
        "page_token": bool(PAGE_ACCESS_TOKEN),
        "openai_key": bool(OPENAI_API_KEY)
    })

# ===============================
# Verificación webhook (Meta)
# ===============================
@app.route("/webhook", methods=["GET"])
def verify():
    if request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge")
    return "Verificación fallida", 403

# ===============================
# Webhook POST (Mensajes)
# ===============================
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("\n" + "=" * 60)
    print("Mensaje recibido:", data)

    if "entry" in data:
        for entry in data["entry"]:
            for event in entry.get("messaging", []):
                sender_id = event["sender"]["id"]

                if "message" in event and "text" in event["message"]:
                    user_text = event["message"]["text"]
                    print(f"Mensaje de {sender_id}: {user_text}")

                    try:
                        completion = client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=[
                                {"role": "system", "content": SYSTEM_CONTEXT},
                                {"role": "user", "content": user_text}
                            ]
                        )

                        reply = completion.choices[0].message.content
                        send_message(sender_id, reply)

                    except Exception as e:
                        print("❌ Error OpenAI:", str(e))
                        send_message(
                            sender_id,
                            "Lo siento, ocurrió un error. Intenta más tarde."
                        )

    print("=" * 60 + "\n")
    return "OK", 200

# ===============================
# Ejecutar app
# ===============================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
