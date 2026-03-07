"""
Gupshup WhatsApp Business API Integration Service
Handles sending and receiving WhatsApp messages for OEMLinker
"""
import os
import httpx
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Gupshup Configuration
GUPSHUP_API_URL = "https://api.gupshup.io/wa/api/v1/msg"
GUPSHUP_MEDIA_URL = "https://mediaapi.smsgupshup.com/GatewayAPI/rest"
GUPSHUP_APP_NAME = os.environ.get("GUPSHUP_APP_NAME", "OEMLinker")
GUPSHUP_API_KEY = os.environ.get("GUPSHUP_API_KEY", "")
GUPSHUP_SOURCE_NUMBER = os.environ.get("GUPSHUP_SOURCE_NUMBER", "")  # WhatsApp Business Number


class WhatsAppService:
    """Service for sending WhatsApp messages via Gupshup API"""
    
    def __init__(self):
        self.api_url = GUPSHUP_API_URL
        self.app_name = GUPSHUP_APP_NAME
        self.api_key = GUPSHUP_API_KEY
        self.source_number = GUPSHUP_SOURCE_NUMBER
    
    def is_configured(self) -> bool:
        """Check if WhatsApp service is properly configured"""
        return bool(self.api_key and self.source_number)
    
    async def send_text_message(
        self, 
        to_number: str, 
        message: str
    ) -> Dict[str, Any]:
        """
        Send a text message via WhatsApp
        
        Args:
            to_number: Recipient phone number in E.164 format (e.g., 919876543210)
            message: Text message content
            
        Returns:
            API response dict
        """
        if not self.is_configured():
            logger.warning("WhatsApp service not configured")
            return {"success": False, "error": "WhatsApp not configured"}
        
        # Normalize phone number - remove + if present
        to_number = to_number.replace("+", "").replace(" ", "").replace("-", "")
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "apikey": self.api_key
        }
        
        # Message must be JSON encoded for Gupshup WhatsApp API
        import json
        message_payload = json.dumps({
            "type": "text",
            "text": message
        })
        
        payload = {
            "channel": "whatsapp",
            "source": self.source_number,
            "destination": to_number,
            "message": message_payload,
            "src.name": self.app_name
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url,
                    headers=headers,
                    data=payload,
                    timeout=30.0
                )
                
                result = response.json() if response.text else {}
                
                if response.status_code in [200, 201, 202]:
                    logger.info(f"WhatsApp message sent to {to_number[:6]}***")
                    return {
                        "success": True, 
                        "message_id": result.get("messageId"),
                        "response": result
                    }
                else:
                    logger.error(f"WhatsApp send failed: {result}")
                    return {
                        "success": False, 
                        "error": result.get("message", "Send failed"),
                        "response": result
                    }
                    
        except Exception as e:
            logger.error(f"WhatsApp API error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def upload_media(
        self,
        file_data: bytes,
        file_name: str = "audio.mp3",
        content_type: str = "audio/mpeg"
    ) -> Dict[str, Any]:
        """
        Upload media file to Gupshup for sending via WhatsApp
        
        Args:
            file_data: Binary file data
            file_name: Name of the file
            content_type: MIME type (audio/mpeg, audio/ogg, etc.)
            
        Returns:
            Dict with media_id or error
        """
        if not self.is_configured():
            return {"success": False, "error": "WhatsApp not configured"}
        
        try:
            # Gupshup media upload endpoint
            upload_url = f"{GUPSHUP_MEDIA_URL}/{self.source_number}"
            
            headers = {
                "apikey": self.api_key
            }
            
            # Create multipart form data
            files = {
                "file": (file_name, file_data, content_type)
            }
            
            data = {
                "file_type": content_type
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    upload_url,
                    headers=headers,
                    files=files,
                    data=data,
                    timeout=60.0
                )
                
                result = response.json() if response.text else {}
                
                if response.status_code in [200, 201, 202] and result.get("status") == "success":
                    media_id = result.get("mediaId")
                    logger.info(f"Media uploaded successfully: {media_id}")
                    return {
                        "success": True,
                        "media_id": media_id,
                        "response": result
                    }
                else:
                    logger.error(f"Media upload failed: {result}")
                    return {
                        "success": False,
                        "error": result.get("message", "Upload failed"),
                        "response": result
                    }
                    
        except Exception as e:
            logger.error(f"Media upload error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def send_audio_message(
        self,
        to_number: str,
        audio_data: bytes,
        file_name: str = "voice_response.mp3"
    ) -> Dict[str, Any]:
        """
        Send an audio/voice message via WhatsApp using base64 encoding
        
        Args:
            to_number: Recipient phone number
            audio_data: Audio file bytes (MP3)
            file_name: Name of the audio file
            
        Returns:
            API response dict
        """
        if not self.is_configured():
            return {"success": False, "error": "WhatsApp not configured"}
        
        import base64
        
        # Encode audio as base64
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        to_number = to_number.replace("+", "").replace(" ", "").replace("-", "")
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "apikey": self.api_key
        }
        
        import json
        # Send audio with base64 data
        message_payload = json.dumps({
            "type": "audio",
            "audio": {
                "data": audio_base64,
                "filename": file_name
            }
        })
        
        payload = {
            "channel": "whatsapp",
            "source": self.source_number,
            "destination": to_number,
            "message": message_payload,
            "src.name": self.app_name
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url,
                    headers=headers,
                    data=payload,
                    timeout=60.0  # Longer timeout for audio
                )
                
                result = response.json() if response.text else {}
                
                if response.status_code in [200, 201, 202]:
                    logger.info(f"Audio message sent to {to_number[:6]}***")
                    return {
                        "success": True,
                        "message_id": result.get("messageId"),
                        "response": result
                    }
                else:
                    logger.error(f"Audio message send failed: {result}")
                    return {
                        "success": False,
                        "error": result.get("message", "Send failed"),
                        "response": result
                    }
                    
        except Exception as e:
            logger.error(f"Audio message API error: {str(e)}")
            return {"success": False, "error": str(e)}

    async def send_template_message(
        self,
        to_number: str,
        template_id: str,
        params: list = None
    ) -> Dict[str, Any]:
        """
        Send a template message via WhatsApp (for business-initiated messages)
        
        Args:
            to_number: Recipient phone number
            template_id: Approved template ID
            params: List of template parameters
            
        Returns:
            API response dict
        """
        if not self.is_configured():
            return {"success": False, "error": "WhatsApp not configured"}
        
        to_number = to_number.replace("+", "").replace(" ", "").replace("-", "")
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "apikey": self.api_key
        }
        
        # Build template message
        template_message = {
            "id": template_id,
            "params": params or []
        }
        
        payload = {
            "channel": "whatsapp",
            "source": self.source_number,
            "destination": to_number,
            "template": str(template_message),
            "src.name": self.app_name
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url,
                    headers=headers,
                    data=payload,
                    timeout=30.0
                )
                
                result = response.json() if response.text else {}
                
                if response.status_code in [200, 201, 202]:
                    logger.info(f"WhatsApp template message sent to {to_number[:6]}***")
                    return {"success": True, "response": result}
                else:
                    logger.error(f"WhatsApp template send failed: {result}")
                    return {"success": False, "error": result.get("message", "Send failed")}
                    
        except Exception as e:
            logger.error(f"WhatsApp template API error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def send_interactive_message(
        self,
        to_number: str,
        body_text: str,
        buttons: list = None,
        header_text: str = None,
        footer_text: str = None
    ) -> Dict[str, Any]:
        """
        Send an interactive message with buttons
        
        Args:
            to_number: Recipient phone number
            body_text: Main message body
            buttons: List of button dicts with 'id' and 'title'
            header_text: Optional header
            footer_text: Optional footer
            
        Returns:
            API response dict
        """
        if not self.is_configured():
            return {"success": False, "error": "WhatsApp not configured"}
        
        to_number = to_number.replace("+", "").replace(" ", "").replace("-", "")
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "apikey": self.api_key
        }
        
        # Build interactive message structure
        interactive = {
            "type": "button",
            "body": {"text": body_text}
        }
        
        if header_text:
            interactive["header"] = {"type": "text", "text": header_text}
        
        if footer_text:
            interactive["footer"] = {"text": footer_text}
        
        if buttons:
            interactive["action"] = {
                "buttons": [
                    {"type": "reply", "reply": {"id": btn["id"], "title": btn["title"][:20]}}
                    for btn in buttons[:3]  # Max 3 buttons
                ]
            }
        
        import json
        payload = {
            "channel": "whatsapp",
            "source": self.source_number,
            "destination": to_number,
            "message": json.dumps({"type": "interactive", "interactive": interactive}),
            "src.name": self.app_name
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url,
                    headers=headers,
                    data=payload,
                    timeout=30.0
                )
                
                result = response.json() if response.text else {}
                
                if response.status_code in [200, 201, 202]:
                    return {"success": True, "response": result}
                else:
                    return {"success": False, "error": result.get("message", "Send failed")}
                    
        except Exception as e:
            logger.error(f"WhatsApp interactive API error: {str(e)}")
            return {"success": False, "error": str(e)}


def parse_webhook_message(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Parse incoming Gupshup webhook payload
    
    Returns:
        Parsed message dict with sender, text, type, etc.
    """
    try:
        # Gupshup webhook format
        message_type = payload.get("type", "")
        
        if message_type == "message":
            message_payload = payload.get("payload", {})
            sender = message_payload.get("source", "")
            
            # Get message content
            msg_type = message_payload.get("type", "text")
            
            parsed = {
                "sender": sender,
                "message_id": message_payload.get("id"),
                "timestamp": payload.get("timestamp"),
                "type": msg_type,
                "app_name": payload.get("app"),
            }
            
            if msg_type == "text":
                parsed["text"] = message_payload.get("payload", {}).get("text", "")
            elif msg_type == "button_reply":
                parsed["button_id"] = message_payload.get("payload", {}).get("id", "")
                parsed["button_title"] = message_payload.get("payload", {}).get("title", "")
            elif msg_type == "image":
                parsed["image_url"] = message_payload.get("payload", {}).get("url", "")
                parsed["caption"] = message_payload.get("payload", {}).get("caption", "")
            elif msg_type == "document":
                parsed["document_url"] = message_payload.get("payload", {}).get("url", "")
                parsed["filename"] = message_payload.get("payload", {}).get("filename", "")
            elif msg_type in ["audio", "voice"]:
                parsed["audio_url"] = message_payload.get("payload", {}).get("url", "")
                parsed["type"] = "audio"
            
            return parsed
            
        elif message_type == "message-event":
            # Delivery status updates
            return {
                "type": "status",
                "status": payload.get("payload", {}).get("type", ""),
                "message_id": payload.get("payload", {}).get("id", ""),
                "destination": payload.get("payload", {}).get("destination", "")
            }
            
    except Exception as e:
        logger.error(f"Webhook parse error: {str(e)}")
    
    return None


# Singleton instance
whatsapp_service = WhatsAppService()


async def download_audio_from_url(audio_url: str) -> Optional[bytes]:
    """Download audio file from Gupshup URL"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(audio_url, timeout=30.0)
            if response.status_code == 200:
                return response.content
    except Exception as e:
        logger.error(f"Failed to download audio: {str(e)}")
    return None
