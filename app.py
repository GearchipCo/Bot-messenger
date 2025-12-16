from flask import Flask, request, jsonify
import requests
import os
import json
import logging
from openai import OpenAI
from datetime import datetime

# ===============================
# Configuración inicial
# ===============================
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Variables de entorno
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Cliente OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)

# ===============================
# Cargar conocimientos (JSON)
# ===============================
def cargar_conocimientos():
    """Carga el archivo JSON de conocimientos"""
    try:
        # Intentar varias rutas posibles
        rutas_posibles = [
            "conocimientos.json",
            "./conocimientos.json",
            "/app/conocimientos.json",  # Para Render/Docker
            os.path.join(os.path.dirname(__file__), "conocimientos.json")
        ]
        
        conocimiento_cargado = None
        ruta_usada = None
        
        for ruta in rutas_posibles:
            if os.path.exists(ruta):
                with open(ruta, "r", encoding="utf-8") as f:
                    conocimiento_cargado = json.load(f)
                ruta_usada = ruta
                logger.info(f"✅ Conocimientos cargados desde: {ruta}")
                break
        
        if conocimiento_cargado is None:
            logger.error("❌ No se encontró el archivo conocimientos.json")
            # Crear estructura básica para no fallar
            conocimiento_cargado = {
                "universidad": {
                    "nombre": "ITESA",
                    "nombre_corto": "ITESA"
                },
                "contacto": {
                    "telefonos": {
                        "principal": "+52 748 912 4450"
                    }
                }
            }
        
        return conocimiento_cargado
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ Error en formato JSON: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"❌ Error cargando conocimientos: {str(e)}")
        raise

# Cargar conocimientos al inicio
CONOCIMIENTOS = cargar_conocimientos()

# ===============================
# Crear contexto para OpenAI
# ===============================
def crear_contexto_sistema():
    """Crea el contexto del sistema para OpenAI"""
    
    try:
        # Extraer información clave
        uni = CONOCIMIENTOS.get("universidad", {})
        contacto = CONOCIMIENTOS.get("contacto", {})
        carreras = CONOCIMIENTOS.get("carreras", [])
        admision = CONOCIMIENTOS.get("admision", {})
        costos = CONOCIMIENTOS.get("costos", {})
        
        # Construir contexto estructurado
        contexto = f"""
# ASISTENTE OFICIAL DEL {uni.get('nombre', 'ITESA').upper()}

## INFORMACIÓN INSTITUCIONAL
- Nombre: {uni.get('nombre', 'ITESA')}
- Tipo: {uni.get('tipo', 'Tecnológico')}
- Eslogan: {uni.get('eslogan', '')}

## CONTACTO
- Teléfono principal: {contacto.get('telefonos', {}).get('principal', 'No disponible')}
- WhatsApp: {contacto.get('telefonos', {}).get('whatsapp', 'No disponible')}
- Correo general: {contacto.get('correos', {}).get('general', 'No disponible')}
- Dirección: {contacto.get('direccion', {}).get('completa', 'No disponible')}
- Sitio web: {contacto.get('sitio_web', 'No disponible')}

## CARRERAS DISPONIBLES
"""
        
        # Agregar información de carreras
        for carrera in carreras:
            contexto += f"""
- {carrera.get('nombre', 'Carrera')} ({carrera.get('abreviatura', '')})
  * Duración: {carrera.get('duracion', 'No especificada')}
  * Modalidad: {carrera.get('modalidad', 'Escolarizada')}
  * Turnos: {', '.join(carrera.get('turnos', []))}
  * Título: {carrera.get('titulo', '')}
"""
        
        # Agregar información de admisión
        contexto += f"""
## PROCESO DE ADMISIÓN
{chr(10).join(admision.get('proceso', ['No disponible']))}

### Requisitos documentales:
{chr(10).join(admision.get('requisitos', {}).get('documentos', ['No disponible']))}

## COSTOS
- Inscripción: {costos.get('inscripcion', 'No disponible')}
- Colegiatura mensual: {costos.get('colegiatura_mensual', 'No disponible')}

## INSTRUCCIONES PARA EL ASISTENTE:
1. Responde ÚNICAMENTE con la información proporcionada arriba
2. SIEMPRE verifica que los datos sean exactos
3. NO inventes información, fechas, costos o requisitos
4. Si no sabes algo, di: "No tengo esa información específica. Te sugiero contactar al {contacto.get('telefonos', {}).get('principal', '748 912 4450')}"
5. Responde en español, de manera clara y profesional
6. Organiza la información usando viñetas cuando sea útil
7. Sé amable y servicial en todo momento
8. Refiere al contacto oficial cuando sea necesario
"""
        
        return contexto
        
    except Exception as e:
        logger.error(f"❌ Error creando contexto: {str(e)}")
        return "Eres un asistente del ITESA. Responde de manera profesional y clara."

# Crear contexto del sistema
SYSTEM_CONTEXT = crear_contexto_sistema()
logger.info("✅ Contexto del sistema creado exitosamente")

# ===============================
# Enviar mensaje a Facebook
# ===============================
def send_message(recipient_id, text):
    """Envía mensaje a través de Facebook Messenger"""
    
    if not PAGE_ACCESS_TOKEN:
        logger.error("❌ PAGE_ACCESS_TOKEN no configurado")
        return False
    
    url = f"https://graph.facebook.com/v18.0/me/messages"
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text}
    }
    params = {"access_token": PAGE_ACCESS_TOKEN}
    
    try:
        response = requests.post(url, params=params, json=payload, timeout=10)
        
        if response.status_code == 200:
            logger.info(f"✅ Mensaje enviado a {recipient_id[:8]}...")
            return True
        else:
            logger.error(f"❌ Error Facebook API: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error enviando mensaje: {str(e)}")
        return False

# ===============================
# Obtener respuesta de OpenAI
# ===============================
def obtener_respuesta_openai(pregunta_usuario):
    """Obtiene respuesta de OpenAI usando el contexto"""
    
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_CONTEXT},
                {"role": "user", "content": pregunta_usuario}
            ],
            temperature=0.3,  # Baja temperatura para respuestas precisas
            max_tokens=500
        )
        
        respuesta = completion.choices[0].message.content
        logger.info(f"✅ Respuesta OpenAI generada: {respuesta[:100]}...")
        return respuesta
        
    except Exception as e:
        logger.error(f"❌ Error OpenAI: {str(e)}")
        return f"Lo siento, estoy teniendo dificultades técnicas. Por favor, contacta directamente al {CONOCIMIENTOS.get('contacto', {}).get('telefonos', {}).get('principal', '748 912 4450')}"

# ===============================
# Rutas Flask
# ===============================
@app.route("/", methods=["GET"])
def home():
    nombre = CONOCIMIENTOS.get("universidad", {}).get("nombre_corto", "ITESA")
    return f"🤖 Asistente {nombre} - En línea 🚀", 200

@app.route("/debug", methods=["GET"])
def debug():
    """Endpoint de depuración"""
    return jsonify({
        "status": "running",
        "universidad": CONOCIMIENTOS.get("universidad", {}).get("nombre", "ITESA"),
        "telefono": CONOCIMIENTOS.get("contacto", {}).get("telefonos", {}).get("principal", "No disponible"),
        "carreras": len(CONOCIMIENTOS.get("carreras", [])),
        "contexto_length": len(SYSTEM_CONTEXT),
        "timestamp": datetime.now().isoformat()
    })

@app.route("/conocimientos", methods=["GET"])
def ver_conocimientos():
    """Muestra la estructura de conocimientos cargada"""
    return jsonify({
        "universidad": CONOCIMIENTOS.get("universidad"),
        "carreras_count": len(CONOCIMIENTOS.get("carreras", [])),
        "contacto": CONOCIMIENTOS.get("contacto", {}).get("telefonos")
    })

@app.route("/webhook", methods=["GET"])
def verify():
    """Verificación del webhook de Facebook"""
    token_recibido = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    
    logger.info(f"🔐 Verificación recibida. Token esperado: {VERIFY_TOKEN}, Token recibido: {token_recibido}")
    
    if token_recibido == VERIFY_TOKEN:
        logger.info("✅ Verificación exitosa")
        return challenge
    else:
        logger.error("❌ Verificación fallida")
        return "Token de verificación incorrecto", 403

@app.route("/webhook", methods=["POST"])
def webhook():
    """Recibe mensajes de Facebook"""
    data = request.json
    
    if not data:
        logger.warning("❌ Webhook POST sin datos")
        return "No data", 400
    
    logger.info(f"📥 Webhook recibido: {json.dumps(data)[:500]}...")
    
    try:
        if "entry" in data:
            for entry in data["entry"]:
                for event in entry.get("messaging", []):
                    # Ignorar mensajes echo (los que nosotros enviamos)
                    if event.get("message", {}).get("is_echo"):
                        continue
                    
                    sender_id = event["sender"]["id"]
                    
                    if "message" in event and "text" in event["message"]:
                        user_text = event["message"]["text"]
                        
                        logger.info(f"💬 Usuario {sender_id[:8]}...: {user_text}")
                        
                        # Obtener respuesta inteligente
                        respuesta = obtener_respuesta_openai(user_text)
                        
                        # Enviar respuesta
                        send_message(sender_id, respuesta)
                        
        return "OK", 200
        
    except Exception as e:
        logger.error(f"❌ Error procesando webhook: {str(e)}")
        return "Error interno", 500

# ===============================
# Inicialización
# ===============================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    
    print("\n" + "="*60)
    print("🚀 ASISTENTE ITESA - INICIANDO")
    print("="*60)
    print(f"🏫 Institución: {CONOCIMIENTOS.get('universidad', {}).get('nombre', 'ITESA')}")
    print(f"📞 Teléfono: {CONOCIMIENTOS.get('contacto', {}).get('telefonos', {}).get('principal', 'No disponible')}")
    print(f"🎓 Carreras: {len(CONOCIMIENTOS.get('carreras', []))}")
    print(f"🌐 Puerto: {port}")
    print("="*60 + "\n")
    
    app.run(host="0.0.0.0", port=port, debug=False)
