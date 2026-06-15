import requests
from app.core.config import settings

def send_whatsapp_message(to_phone: str, text_body: str):
    """
    Sends a text message to a user via Meta's Graph API using synchronous requests.
    """
    url = f"https://graph.facebook.com/v20.0/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    
    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_phone,
        "type": "text",
        "text": {
            "preview_url": False,
            "body": text_body
        }
    }
    
    try:
        # We use requests.post instead of httpx so it executes immediately
        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code == 200:
            print(f"✅ [WhatsApp] Message sent successfully to {to_phone}")
        else:
            print(f"❌ [WhatsApp Error] Failed to send: {response.text}")
            
    except Exception as e:
        print(f"❌ [WhatsApp Exception] {str(e)}")