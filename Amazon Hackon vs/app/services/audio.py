import os
import requests
import tempfile
from google import genai
from app.core.config import settings

# Initialize the Gemini Client
client = genai.Client(api_key=settings.GEMINI_API_KEY)

def process_voice_note_to_text(audio_id: str, bucket_name: str = None) -> str:
    """
    Downloads the voice note from WhatsApp and uses Gemini to transcribe it natively.
    (Note: bucket_name is kept in the parameters so routes.py doesn't break, but we ignore it).
    """
    try:
        print("📥 Fetching audio URL from WhatsApp...")
        headers = {"Authorization": f"Bearer {settings.WHATSAPP_API_TOKEN}"}
        
        # 1. Ask Meta for the actual media URL using the audio_id
        # Note: Check your Graph API version. v19.0 or v20.0 is standard.
        url_res = requests.get(f"https://graph.facebook.com/v19.0/{audio_id}", headers=headers)
        url_data = url_res.json()
        
        media_url = url_data.get("url")
        if not media_url:
            print(f"❌ Failed to get media URL: {url_data}")
            return ""
            
        # 2. Download the audio file from WhatsApp
        print("📥 Downloading audio file...")
        media_res = requests.get(media_url, headers=headers)
        
        # 3. Save it to a temporary local file so Gemini can read it
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as temp_audio:
            temp_audio.write(media_res.content)
            temp_file_path = temp_audio.name
            
        try:
            # 4. Upload and Transcribe with Gemini!
            print("🧠 [Gemini] Listening to voice note...")
            audio_file = client.files.upload(file=temp_file_path)
            
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    audio_file, 
                    "You are an expert transcriber for an Indian grocery bot. "
                    "Listen to this voice note. The user might speak in Hindi, English, or Hinglish. "
                    "Transcribe EXACTLY what they said. Return ONLY the transcribed text, with no extra commentary, formatting, or quotes."
                ]
            )
            
            transcription = response.text.strip()
            print(f"✅ [Transcribed]: {transcription}")
            
            # 5. Cleanup the file from Gemini's servers to save space
            client.files.delete(name=audio_file.name)
            
            return transcription
            
        finally:
            # 6. Delete the temporary file off your Mac
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                
    except Exception as e:
        print(f"❌ [Audio Processing Error]: {str(e)}")
        return ""