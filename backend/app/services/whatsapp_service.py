"""
Gupshup WhatsApp Business API Integration Service
Handles sending and receiving WhatsApp messages for OEMLinker
"""
import os
import httpx
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Gupshup Configuration
GUPSHUP_API_URL = "https://api.gupshup.io/wa/api/v1/msg"
GUPSHUP_TEMPLATE_URL = "https://api.gupshup.io/wa/api/v1/template/msg"
GUPSHUP_PARTNER_URL = "https://partner.gupshup.io/partner/app"
GUPSHUP_MEDIA_URL = "https://mediaapi.smsgupshup.com/GatewayAPI/rest"
GUPSHUP_APP_NAME = os.environ.get("GUPSHUP_APP_NAME", "OEMLinker")
GUPSHUP_API_KEY = os.environ.get("GUPSHUP_API_KEY", "")
GUPSHUP_SOURCE_NUMBER = os.environ.get("GUPSHUP_SOURCE_NUMBER", "")  # WhatsApp Business Number
GUPSHUP_APP_ID = os.environ.get("GUPSHUP_APP_ID", "")  # Gupshup App ID for partner APIs


class WhatsAppService:
    """Service for sending WhatsApp messages via Gupshup API"""
    
    def __init__(self):
        self.api_url = GUPSHUP_API_URL
        self.template_url = GUPSHUP_TEMPLATE_URL
        self.partner_url = GUPSHUP_PARTNER_URL
        self.app_name = GUPSHUP_APP_NAME
        self.api_key = GUPSHUP_API_KEY
        self.source_number = GUPSHUP_SOURCE_NUMBER
        self.app_id = GUPSHUP_APP_ID
    
    def is_configured(self) -> bool:
        """Check if WhatsApp service is properly configured"""
        return bool(self.api_key and self.source_number)
    
    async def get_templates(self) -> Dict[str, Any]:
        """
        Fetch approved WhatsApp templates from Gupshup Partner API
        
        Returns:
            Dict with templates list or error
        """
        if not self.is_configured():
            return {"success": False, "error": "WhatsApp not configured", "templates": []}
        
        # Try Partner API first if app_id is available
        if self.app_id:
            try:
                headers = {
                    "apikey": self.api_key,
                    "Content-Type": "application/json"
                }
                
                # Gupshup Partner API endpoint for templates
                url = f"{self.partner_url}/{self.app_id}/templates"
                
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        url,
                        headers=headers,
                        timeout=30.0
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        templates = data.get("templates", data.get("data", []))
                        
                        # Normalize template format
                        normalized = []
                        for t in templates:
                            normalized.append({
                                "id": t.get("id") or t.get("elementName") or t.get("name"),
                                "name": t.get("elementName") or t.get("name", ""),
                                "status": t.get("status", "UNKNOWN"),
                                "category": t.get("category", t.get("templateType", "UNKNOWN")),
                                "language": t.get("languageCode", t.get("language", "en")),
                                "content": t.get("data", t.get("content", t.get("body", ""))),
                                "header": t.get("header"),
                                "footer": t.get("footer"),
                                "buttons": t.get("buttons", []),
                                "created_at": t.get("createdOn", t.get("created_at")),
                                "modified_at": t.get("modifiedOn", t.get("modified_at"))
                            })
                        
                        # Filter only approved templates
                        approved = [t for t in normalized if t["status"].upper() in ["APPROVED", "ACTIVE", "ENABLED"]]
                        
                        logger.info(f"Fetched {len(approved)} approved templates from Gupshup")
                        return {
                            "success": True,
                            "templates": approved,
                            "total": len(approved),
                            "source": "gupshup_partner_api"
                        }
                    else:
                        logger.warning(f"Partner API returned {response.status_code}: {response.text}")
                        
            except Exception as e:
                logger.error(f"Partner API error: {str(e)}")
        
        # Fallback: Try the regular API endpoint
        try:
            headers = {
                "apikey": self.api_key,
                "Content-Type": "application/json"
            }
            
            # Alternative endpoint - fetch template list
            url = f"https://api.gupshup.io/wa/app/{self.source_number}/template/list"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=headers,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    templates = data.get("templates", data.get("data", []))
                    
                    normalized = []
                    for t in templates:
                        normalized.append({
                            "id": t.get("id") or t.get("elementName"),
                            "name": t.get("elementName") or t.get("name", ""),
                            "status": t.get("status", "UNKNOWN"),
                            "category": t.get("category", "UNKNOWN"),
                            "language": t.get("languageCode", "en"),
                            "content": t.get("data", t.get("body", "")),
                            "header": t.get("header"),
                            "footer": t.get("footer"),
                            "buttons": t.get("buttons", [])
                        })
                    
                    approved = [t for t in normalized if t["status"].upper() in ["APPROVED", "ACTIVE", "ENABLED"]]
                    
                    logger.info(f"Fetched {len(approved)} approved templates from Gupshup API")
                    return {
                        "success": True,
                        "templates": approved,
                        "total": len(approved),
                        "source": "gupshup_api"
                    }
                else:
                    logger.warning(f"Template list API returned {response.status_code}")
                    
        except Exception as e:
            logger.error(f"Template list API error: {str(e)}")
        
        return {
            "success": False,
            "error": "Could not fetch templates from Gupshup. Check API credentials.",
            "templates": [],
            "source": "error"
        }
    
    async def send_gupshup_template(
        self,
        to_number: str,
        template_id: str,
        params: List[str] = None
    ) -> Dict[str, Any]:
        """
        Send an approved template message via Gupshup Template API
        
        Args:
            to_number: Recipient phone number
            template_id: Template ID or element name from Gupshup
            params: List of parameter values
            
        Returns:
            API response dict
        """
        if not self.is_configured():
            return {"success": False, "error": "WhatsApp not configured"}
        
        to_number = to_number.replace("+", "").replace(" ", "").replace("-", "")
        if not to_number.startswith("91") and len(to_number) == 10:
            to_number = "91" + to_number
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "apikey": self.api_key
        }
        
        import json
        template_payload = json.dumps({
            "id": template_id,
            "params": params or []
        })
        
        payload = {
            "channel": "whatsapp",
            "source": self.source_number,
            "destination": to_number,
            "template": template_payload,
            "src.name": self.app_name
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.template_url,
                    headers=headers,
                    data=payload,
                    timeout=30.0
                )
                
                result = response.json() if response.text else {}
                
                if response.status_code in [200, 201, 202]:
                    logger.info(f"Template {template_id} sent to {to_number[:6]}***")
                    return {
                        "success": True,
                        "message_id": result.get("messageId"),
                        "response": result
                    }
                else:
                    logger.error(f"Template send failed: {result}")
                    return {
                        "success": False,
                        "error": result.get("message", "Send failed"),
                        "response": result
                    }
                    
        except Exception as e:
            logger.error(f"Template send error: {str(e)}")
            return {"success": False, "error": str(e)}
    
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
        
        # Build template message in Gupshup format
        import json
        template_message = json.dumps({
            "id": template_id,
            "params": params or []
        })
        
        payload = {
            "channel": "whatsapp",
            "source": self.source_number,
            "destination": to_number,
            "template": template_message,
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


async def send_document_message(
    to_number: str,
    document_url: str,
    filename: str,
    caption: str = ""
) -> Dict[str, Any]:
    """
    Send a document/file via WhatsApp using URL
    
    Args:
        to_number: Recipient phone number
        document_url: Public URL of the document
        filename: Display filename
        caption: Optional caption
        
    Returns:
        API response dict
    """
    if not whatsapp_service.is_configured():
        return {"success": False, "error": "WhatsApp not configured"}
    
    to_number = to_number.replace("+", "").replace(" ", "").replace("-", "")
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "apikey": whatsapp_service.api_key
    }
    
    import json
    message_payload = json.dumps({
        "type": "file",
        "url": document_url,
        "filename": filename,
        "caption": caption
    })
    
    payload = {
        "channel": "whatsapp",
        "source": whatsapp_service.source_number,
        "destination": to_number,
        "message": message_payload,
        "src.name": whatsapp_service.app_name
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                whatsapp_service.api_url,
                headers=headers,
                data=payload,
                timeout=60.0
            )
            
            result = response.json() if response.text else {}
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"Document sent to {to_number[:6]}***: {filename}")
                return {
                    "success": True,
                    "message_id": result.get("messageId"),
                    "response": result
                }
            else:
                logger.error(f"Document send failed: {result}")
                return {
                    "success": False,
                    "error": result.get("message", "Send failed"),
                    "response": result
                }
                
    except Exception as e:
        logger.error(f"Document send API error: {str(e)}")
        return {"success": False, "error": str(e)}


async def send_image_message(
    to_number: str,
    image_url: str,
    caption: str = ""
) -> Dict[str, Any]:
    """
    Send an image via WhatsApp using URL
    
    Args:
        to_number: Recipient phone number
        image_url: Public URL of the image
        caption: Optional caption
        
    Returns:
        API response dict
    """
    if not whatsapp_service.is_configured():
        return {"success": False, "error": "WhatsApp not configured"}
    
    to_number = to_number.replace("+", "").replace(" ", "").replace("-", "")
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "apikey": whatsapp_service.api_key
    }
    
    import json
    message_payload = json.dumps({
        "type": "image",
        "originalUrl": image_url,
        "previewUrl": image_url,
        "caption": caption
    })
    
    payload = {
        "channel": "whatsapp",
        "source": whatsapp_service.source_number,
        "destination": to_number,
        "message": message_payload,
        "src.name": whatsapp_service.app_name
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                whatsapp_service.api_url,
                headers=headers,
                data=payload,
                timeout=60.0
            )
            
            result = response.json() if response.text else {}
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"Image sent to {to_number[:6]}***")
                return {
                    "success": True,
                    "message_id": result.get("messageId"),
                    "response": result
                }
            else:
                logger.error(f"Image send failed: {result}")
                return {
                    "success": False,
                    "error": result.get("message", "Send failed"),
                    "response": result
                }
                
    except Exception as e:
        logger.error(f"Image send API error: {str(e)}")
        return {"success": False, "error": str(e)}
