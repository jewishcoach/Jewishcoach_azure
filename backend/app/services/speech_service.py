import os
import requests
from dotenv import load_dotenv

load_dotenv()

class SpeechService:
    def __init__(self):
        self.speech_key = os.getenv("AZURE_SPEECH_KEY")
        self.speech_region = os.getenv("AZURE_SPEECH_REGION")
    
    def get_token(self) -> tuple[str, str]:
        """
        Generate a temporary token for frontend to use with Azure Speech.
        Token is valid for 10 minutes.
        """
        fetch_token_url = f"https://{self.speech_region}.api.cognitive.microsoft.com/sts/v1.0/issueToken"
        
        headers = {
            'Ocp-Apim-Subscription-Key': self.speech_key
        }
        
        response = requests.post(fetch_token_url, headers=headers)
        response.raise_for_status()
        
        return response.text, self.speech_region






