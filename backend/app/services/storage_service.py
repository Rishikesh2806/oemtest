"""
Cloud Storage Service
Handles file uploads/downloads for OEMLinker (machine images, drawings)
"""
import os
import uuid
import logging
import requests
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Storage Configuration
STORAGE_URL = "https://integrations.emergentagent.com/objstore/api/v1/storage"
EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY")
APP_NAME = "oemlinker"

# Module-level storage key (initialized once)
_storage_key: Optional[str] = None

# MIME type mapping
MIME_TYPES = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg", 
    "png": "image/png",
    "gif": "image/gif",
    "webp": "image/webp",
    "pdf": "application/pdf",
    "json": "application/json",
    "csv": "text/csv",
    "txt": "text/plain",
    "dwg": "application/acad",
    "dxf": "application/dxf"
}


def init_storage() -> str:
    """
    Initialize storage and get session-scoped storage key.
    Call ONCE at startup. Returns reusable storage_key.
    """
    global _storage_key
    
    if _storage_key:
        return _storage_key
    
    if not EMERGENT_KEY:
        raise ValueError("EMERGENT_LLM_KEY not configured")
    
    try:
        resp = requests.post(
            f"{STORAGE_URL}/init",
            json={"emergent_key": EMERGENT_KEY},
            timeout=30
        )
        resp.raise_for_status()
        _storage_key = resp.json()["storage_key"]
        logger.info("Cloud storage initialized successfully")
        return _storage_key
    except Exception as e:
        logger.error(f"Failed to initialize cloud storage: {e}")
        raise


def get_storage_key() -> str:
    """Get or initialize storage key"""
    global _storage_key
    if not _storage_key:
        return init_storage()
    return _storage_key


def get_content_type(filename: str) -> str:
    """Get MIME type from filename extension"""
    ext = filename.lower().split(".")[-1] if "." in filename else "bin"
    return MIME_TYPES.get(ext, "application/octet-stream")


def list_files(prefix: str = "") -> dict:
    """
    List files in cloud storage with optional prefix filter.
    
    Args:
        prefix: Path prefix to filter (e.g., "oemlinker/machines")
    
    Returns:
        dict with 'files' list
    """
    key = get_storage_key()
    
    try:
        params = {}
        if prefix:
            params["prefix"] = prefix
            
        resp = requests.get(
            f"{STORAGE_URL}/objects",
            headers={"X-Storage-Key": key},
            params=params,
            timeout=30
        )
        resp.raise_for_status()
        data = resp.json()
        
        files = data.get("objects", data.get("files", []))
        
        # Normalize file info
        normalized = []
        for f in files:
            if isinstance(f, str):
                normalized.append({
                    "path": f,
                    "name": f.split("/")[-1],
                    "size": 0,
                    "storage_url": f"/api/storage/{f}"
                })
            else:
                normalized.append({
                    "path": f.get("path", f.get("key", "")),
                    "name": f.get("path", f.get("key", "")).split("/")[-1],
                    "size": f.get("size", 0),
                    "content_type": f.get("content_type", ""),
                    "created_at": f.get("created_at", f.get("last_modified")),
                    "storage_url": f"/api/storage/{f.get('path', f.get('key', ''))}"
                })
        
        return {"success": True, "files": normalized, "total": len(normalized)}
    except Exception as e:
        logger.error(f"Failed to list files: {e}")
        return {"success": False, "error": str(e), "files": []}


def delete_file(path: str) -> dict:
    """
    Delete a file from cloud storage.
    
    Args:
        path: Storage path to delete
    
    Returns:
        dict with success status
    """
    key = get_storage_key()
    
    try:
        resp = requests.delete(
            f"{STORAGE_URL}/objects/{path}",
            headers={"X-Storage-Key": key},
            timeout=30
        )
        resp.raise_for_status()
        logger.info(f"File deleted from cloud storage: {path}")
        return {"success": True, "path": path}
    except Exception as e:
        logger.error(f"Failed to delete file: {e}")
        return {"success": False, "error": str(e)}


def upload_file(
    data: bytes,
    filename: str,
    folder: str = "uploads",
    content_type: Optional[str] = None
) -> dict:
    """
    Upload a file to cloud storage.
    
    Args:
        data: File bytes
        filename: Original filename (used for extension detection)
        folder: Subfolder path (e.g., "machines", "drawings")
        content_type: MIME type (auto-detected if not provided)
    
    Returns:
        dict with 'path', 'size', 'url' keys
    """
    key = get_storage_key()
    
    # Generate unique path
    ext = filename.lower().split(".")[-1] if "." in filename else "bin"
    unique_filename = f"{uuid.uuid4()}.{ext}"
    path = f"{APP_NAME}/{folder}/{unique_filename}"
    
    # Detect content type
    if not content_type:
        content_type = get_content_type(filename)
    
    try:
        resp = requests.put(
            f"{STORAGE_URL}/objects/{path}",
            headers={
                "X-Storage-Key": key,
                "Content-Type": content_type
            },
            data=data,
            timeout=120
        )
        resp.raise_for_status()
        result = resp.json()
        
        logger.info(f"File uploaded to cloud storage: {path} ({len(data)} bytes)")
        
        return {
            "path": result["path"],
            "size": result.get("size", len(data)),
            "filename": filename,
            "content_type": content_type,
            "storage_url": f"/api/storage/{result['path']}"
        }
    except Exception as e:
        logger.error(f"Failed to upload file to cloud storage: {e}")
        raise


def download_file(path: str) -> Tuple[bytes, str]:
    """
    Download a file from cloud storage.
    
    Args:
        path: Storage path (e.g., "oemlinker/machines/uuid.jpg")
    
    Returns:
        Tuple of (file_bytes, content_type)
    """
    key = get_storage_key()
    
    try:
        resp = requests.get(
            f"{STORAGE_URL}/objects/{path}",
            headers={"X-Storage-Key": key},
            timeout=60
        )
        resp.raise_for_status()
        
        content_type = resp.headers.get("Content-Type", "application/octet-stream")
        return resp.content, content_type
    except Exception as e:
        logger.error(f"Failed to download file from cloud storage: {e}")
        raise


async def upload_machine_image(
    image_data: bytes,
    filename: str,
    vendor_id: str
) -> dict:
    """
    Upload a machine image to cloud storage.
    
    Args:
        image_data: Image bytes
        filename: Original filename
        vendor_id: Vendor ID for organization
    
    Returns:
        dict with storage details
    """
    folder = f"machines/{vendor_id}"
    return upload_file(image_data, filename, folder)


async def upload_drawing(
    drawing_data: bytes,
    filename: str,
    rfq_id: str
) -> dict:
    """
    Upload an RFQ drawing to cloud storage.
    
    Args:
        drawing_data: Drawing file bytes
        filename: Original filename
        rfq_id: RFQ ID for organization
    
    Returns:
        dict with storage details
    """
    folder = f"drawings/{rfq_id}"
    return upload_file(drawing_data, filename, folder)
