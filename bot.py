import os
from flask import Flask, request, jsonify
import requests
import google.generativeai as genai

app = Flask(__name__)

# Configurar tu API Key de Gemini
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# Configuración de WhatsApp Cloud API
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "mi_token_secreto_123")

PROMPT_SISTEMA = """
Eres un experto en cine y series de televisión para Monterrey, México. El usuario te enviará un enlace de un Short de YouTube o una imagen (screenshot) de una escena. 
Tu tarea es identificar de qué película o serie se trata y devolver obligatoriamente la siguiente información adaptada estrictamente para Monterrey, México:
1. **Título de la película/serie:**
2. **Año de estreno:**
3. **Duración (si es película) o Temporadas y número de capítulos (si es serie):**
4. **Dónde verla en streaming en Monterrey, México:** (Especifica las plataformas de streaming disponibles en la región como Netflix, Max, Prime Video, Disney+, etc., o si está actualmente en cines locales de Monterrey).
"""

# Ruta de verificación del Webhook para Meta
@app.route("/webhook", methods=["GET"])
def verificar_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    
    if mode and token:
        if mode == "subscribe" and token == VERIFY_TOKEN:
            return challenge, 200
        else:
            return "Error de verificación", 403
    return "Servidor activo", 200

# Ruta para recibir los mensajes de WhatsApp
@app.route("/webhook", methods=["POST"])
def webhook():
    body = request.get_json()
    
    try:
        if "entry" in body and "changes" in body["entry"][0]:
            change = body["entry"][0]["changes"][0]["value"]
            if "messages" in change:
                msg = change["messages"][0]
                from_number = msg["from"]
                
                # Mensaje de texto (ej. Enlace de YouTube Short)
                if msg["type"] == "text":
                    texto_usuario = msg["text"]["body"]
                    respuesta = consultar_gemini_texto(texto_usuario)
                    enviar_mensaje_whatsapp(from_number, respuesta)
                
                # Mensaje de imagen (Screenshot)
                elif msg["type"] == "image":
                    image_id = msg["image"]["id"]
                    image_url = obtener_url_imagen_whatsapp(image_id)
                    respuesta = consultar_gemini_imagen(image_url)
                    enviar_mensaje_whatsapp(from_number, respuesta)
                    
        return jsonify({"status": "success"}), 200
    except Exception as e:
        print(f"Error procesando mensaje: {e}")
        return jsonify({"status": "error"}}, 500

def consultar_gemini_texto(texto):
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction=PROMPT_SISTEMA
    )
    response = model.generate_content(f"Analiza este enlace de YouTube Short y dame los datos: {texto}")
    return response.text

def consultar_gemini_imagen(image_url):
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
    img_data = requests.get(image_url, headers=headers).content
    temp_path = "temp_screenshot.jpg"
    with open(temp_path, "wb") as handler:
        handler.write(img_data)
        
    sample_file = genai.upload_file(path=temp_path, display_name="Screenshot Short")
    
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction=PROMPT_SISTEMA
    )
    response = model.generate_content([sample_file, "Identifica la serie o película de este screenshot y dame los datos requeridos."])
    
    if os.path.exists(temp_path):
        os.remove(temp_path)
    return response.text

def obtener_url_imagen_whatsapp(media_id):
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
    r = requests.get(f"https://graph.facebook.com/v18.0/{media_id}", headers=headers)
    return r.json().get("url")

def enviar_mensaje_whatsapp(to, text):
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text},
    }
    requests.post(f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages", headers=headers, json=data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))