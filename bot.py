import os
import requests
from flask import Flask, request, jsonify
from google import genai

app = Flask(__name__)

# Configuración de credenciales desde las variables de entorno de Render
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "cinebot123")
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Inicializar el cliente de Gemini (Google GenAI)
client = genai.Client(api_key=GEMINI_API_KEY)

@app.route("/", methods=["GET"])
def home():
    return "CineBot para Monterrey está activo y funcionando correctamente.", 200

@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode and token:
        if mode == "subscribe" and token == VERIFY_TOKEN:
            return challenge, 200
        else:
            return jsonify({"error": "Token inválido"}), 403
    return jsonify({"error": "Solicitud inválida"}), 400

@app.route("/webhook", methods=["POST"])
def receive_message():
    data = request.get_json()
    print("MENSAJE RECIBIDO DE META:", data)
    
    try:
        if "entry" in data:
            for entry in data["entry"]:
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    if "messages" in value:
                        phone_number_id = value["metadata"]["phone_number_id"]
                        message = value["messages"][0]
                        from_number = message["from"]
                        
                        user_text = ""
                        if "text" in message:
                            user_text = message["text"]["body"]
                        elif "interactive" in message:
                            pass
                        
                        prompt = (
                            f"El usuario en Monterrey envió este contenido o enlace de cine/serie: '{user_text}'. "
                            "Identifica de qué película o serie se trata y responde de forma amigable y útil para "
                            "alguien en Monterrey, indicando en qué plataformas de streaming (Netflix, Max, Disney+, etc.) "
                            "está disponible en México."
                        )

                        response = client.models.generate_content(
                            model="gemini-2.5-flash",
                            contents=prompt,
                        )
                        bot_reply = response.text

                        headers = {
                            "Authorization": f"Bearer {WHATSAPP_TOKEN}",
                            "Content-Type": "application/json"
                        }
                        payload = {
                            "messaging_product": "whatsapp",
                            "to": from_number,
                            "text": {"body": bot_reply}
                        }
                        requests.post(
                            f"https://graph.facebook.com/v18.0/{phone_number_id}/messages",
                            headers=headers,
                            json=payload
                        )

        return jsonify({"status": "success"}), 200
    except Exception as e:
        print(f"Error procesando mensaje: {e}")
        return jsonify({"status": "error"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
