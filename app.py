from flask import Flask, request, jsonify
import requests
import os
from openai import OpenAI
import logging

app = Flask(__name__)

# Configurar logging
logging.basicConfig(level=logging.DEBUG)

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# DEBUG: Verificar variables al inicio
print("=" * 50)
print("DEBUG INICIAL:")
print(f"VERIFY_TOKEN existe: {VERIFY_TOKEN is not None}")
print(f"PAGE_ACCESS_TOKEN existe: {PAGE_ACCESS_TOKEN is not None}")
print(f"OPENAI_API_KEY existe: {OPENAI_API_KEY is not None}")

if PAGE_ACCESS_TOKEN:
    print(f"Longitud PAGE_ACCESS_TOKEN: {len(PAGE_ACCESS_TOKEN)}")
    print(f"Primeros 30 chars: {repr(PAGE_ACCESS_TOKEN[:30])}")
    print(f"Últimos 30 chars: {repr(PAGE_ACCESS_TOKEN[-30:])}")
print("=" * 50)

client = OpenAI(api_key=OPENAI_API_KEY)

def send_message(recipient_id, text):
    print(f"\n{'='*50}")
    print("DEBUG send_message:")
    print(f"Recipient ID: {recipient_id}")
    print(f"Mensaje a enviar: {text}")
    
    if not PAGE_ACCESS_TOKEN:
        print("ERROR: PAGE_ACCESS_TOKEN está vacío!")
        return
    
    # Verificar formato del token
    if not PAGE_ACCESS_TOKEN.startswith('EAA'):
        print(f"ADVERTENCIA: Token no comienza con 'EAA'. Comienza con: {repr(PAGE_ACCESS_TOKEN[:10])}")
    
    url = f"https://graph.facebook.com/v18.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    print(f"URL de API: {url[:100]}...")
    
    data = {
        "recipient": {"id": recipient_id},
        "message": {"text": text}
    }
    
    try:
        response = requests.post(url, json=data, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"FB response: {response.text}")
        
        # Intentar parsear error específico
        if response.status_code != 200:
            try:
                error_data = response.json()
                if 'error' in error_data:
                    print(f"Error Code: {error_data['error'].get('code')}")
                    print(f"Error Type: {error_data['error'].get('type')}")
                    print(f"Error Message: {error_data['error'].get('message')}")
            except:
                pass
                
    except Exception as e:
        print(f"EXCEPCIÓN en requests.post: {str(e)}")
    
    print(f"{'='*50}\n")

@app.route("/", methods=["GET"])
def home():
    return "Bot funcionando", 200

@app.route("/debug", methods=["GET"])
def debug():
    """Endpoint para debugging manual"""
    info = {
        "server_running": True,
        "page_token_exists": PAGE_ACCESS_TOKEN is not None,
        "page_token_length": len(PAGE_ACCESS_TOKEN) if PAGE_ACCESS_TOKEN else 0,
        "verify_token_exists": VERIFY_TOKEN is not None,
        "openai_key_exists": OPENAI_API_KEY is not None,
    }
    return jsonify(info), 200

@app.route("/webhook", methods=["GET"])
def verify():
    print(f"\n{'='*50}")
    print("DEBUG verify (GET):")
    print(f"Token recibido: {request.args.get('hub.verify_token')}")
    print(f"Token esperado: {VERIFY_TOKEN}")
    print(f"Challenge: {request.args.get('hub.challenge')}")
    print(f"{'='*50}\n")
    
    if request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge")
    return "Error de verificación", 403

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print(f"\n{'='*50}")
    print("DEBUG webhook (POST):")
    print(f"Mensaje recibido: {data}")
    
    if "entry" in data:
        for entry in data["entry"]:
            messaging = entry.get("messaging")
            if messaging:
                for message in messaging:
                    sender_id = message["sender"]["id"]
                    if "text" in message.get("message", {}):
                        text = message["message"]["text"]
                        
                        print(f"Procesando mensaje de {sender_id}: {text}")
                        
                        try:
                            # Respuesta con OpenAI
                            completion = client.chat.completions.create(
                                model="gpt-4o-mini",
                                messages=[{"role": "user", "content": text}]
                            )
                            
                            reply = completion.choices[0].message.content
                            print(f"Respuesta de OpenAI: {reply[:100]}...")
                            
                            # Enviar respuesta
                            send_message(sender_id, reply)
                            
                        except Exception as e:
                            print(f"Error procesando con OpenAI: {str(e)}")
                            send_message(sender_id, "Lo siento, hubo un error procesando tu mensaje.")
    
    print(f"{'='*50}\n")
    return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=True)
