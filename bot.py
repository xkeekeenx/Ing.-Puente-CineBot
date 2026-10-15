@app.route("/webhook", methods=["POST"])
def receive_message():
    data = request.get_json()
    print("MENSAJE RECIBIDO DE META:", data)  # <-- Añade esta línea aquí
    
    try:
        # Extraer el mensaje entrante de WhatsApp
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
