"""
AWS S3 Cloud Storage Service
Handles file uploads/downloads for OEMLinker (machine images, drawings)
"""
import os
import uuid
import logging
from typing import Optional, Tuple, List
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

# AWS S3 Configuration
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
AWS_S3_BUCKET_NAME = os.environ.get("AWS_S3_BUCKET_NAME", "oemlinker-storage")
AWS_REGION = os.environ.get("AWS_REGION", "ap-south-1")

# S3 Client (initialized lazily)
_s3_client = None

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


def get_s3_client():
    """Get or create S3 client"""
    global _s3_client
    
    if _s3_client is None:
        if not AWS_ACCESS_KEY_ID or not AWS_SECRET_ACCESS_KEY:
            raise ValueError("AWS credentials not configured")
        
        _s3_client = boto3.client(
            's3',
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION
        )
        logger.info(f"S3 client initialized for bucket: {AWS_S3_BUCKET_NAME}")
    
    return _s3_client


def init_storage() -> str:
    """Initialize S3 storage - verify connection"""
    try:
        client = get_s3_client()
        # Verify bucket exists
        client.head_bucket(Bucket=AWS_S3_BUCKET_NAME)
        logger.info(f"AWS S3 storage initialized: {AWS_S3_BUCKET_NAME}")
        return "s3_initialized"
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        if error_code == '404':
            logger.error(f"S3 bucket {AWS_S3_BUCKET_NAME} does not exist")
        elif error_code == '403':
            logger.error(f"Access denied to S3 bucket {AWS_S3_BUCKET_NAME}")
        raise
    except Exception as e:
        logger.error(f"Failed to initialize S3 storage: {e}")
        raise


def get_content_type(filename: str) -> str:
    """Get MIME type from filename extension"""
    ext = filename.lower().split(".")[-1] if "." in filename else "bin"
    return MIME_TYPES.get(ext, "application/octet-stream")


def upload_file(
    data: bytes,
    filename: str,
    folder: str = "uploads",
    content_type: Optional[str] = None
) -> dict:
    """
    Upload a file to AWS S3.
    
    Args:
        data: File bytes
        filename: Original filename (used for extension detection)
        folder: Subfolder path (e.g., "machines", "drawings")
        content_type: MIME type (auto-detected if not provided)
    
    Returns:
        dict with 'path', 'size', 'url' keys
    """
    client = get_s3_client()
    
    # Generate unique path
    ext = filename.lower().split(".")[-1] if "." in filename else "bin"
    unique_filename = f"{uuid.uuid4()}.{ext}"
    s3_key = f"{folder}/{unique_filename}"
    
    # Detect content type
    if not content_type:
        content_type = get_content_type(filename)
    
    try:
        client.put_object(
            Bucket=AWS_S3_BUCKET_NAME,
            Key=s3_key,
            Body=data,
            ContentType=content_type
        )
        
        # Generate public URL
        public_url = f"https://{AWS_S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"
        
        logger.info(f"File uploaded to S3: {s3_key} ({len(data)} bytes)")
        
        return {
            "path": s3_key,
            "size": len(data),
            "filename": filename,
            "content_type": content_type,
            "url": public_url,
            "storage_url": f"/api/storage/{s3_key}"
        }
    except ClientError as e:
        logger.error(f"Failed to upload file to S3: {e}")
        raise


def download_file(path: str) -> Tuple[bytes, str]:
    """
    Download a file from AWS S3.
    
    Args:
        path: S3 key (e.g., "machines/vendor_id/uuid.jpg")
    
    Returns:
        Tuple of (file_bytes, content_type)
    """
    client = get_s3_client()
    
    try:
        response = client.get_object(Bucket=AWS_S3_BUCKET_NAME, Key=path)
        content = response['Body'].read()
        content_type = response.get('ContentType', 'application/octet-stream')
        return content, content_type
    except ClientError as e:
        logger.error(f"Failed to download file from S3: {e}")
        raise


def list_files(prefix: str = "") -> dict:
    """
    List files in S3 bucket with optional prefix filter.
    
    Args:
        prefix: Path prefix to filter (e.g., "machines")
    
    Returns:
        dict with 'files' list
    """
    client = get_s3_client()
    
    try:
        paginator = client.get_paginator('list_objects_v2')
        
        params = {'Bucket': AWS_S3_BUCKET_NAME}
        if prefix:
            params['Prefix'] = prefix
        
        files = []
        for page in paginator.paginate(**params):
            for obj in page.get('Contents', []):
                key = obj['Key']
                files.append({
                    "path": key,
                    "name": key.split("/")[-1],
                    "size": obj.get('Size', 0),
                    "content_type": get_content_type(key),
                    "created_at": obj.get('LastModified', '').isoformat() if obj.get('LastModified') else None,
                    "url": f"https://{AWS_S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{key}",
                    "storage_url": f"/api/storage/{key}"
                })
        
        return {"success": True, "files": files, "total": len(files)}
    except ClientError as e:
        logger.error(f"Failed to list files from S3: {e}")
        return {"success": False, "error": str(e), "files": []}


def delete_file(path: str) -> dict:
    """
    Delete a file from S3.
    
    Args:
        path: S3 key to delete
    
    Returns:
        dict with success status
    """
    client = get_s3_client()
    
    try:
        client.delete_object(Bucket=AWS_S3_BUCKET_NAME, Key=path)
        logger.info(f"File deleted from S3: {path}")
        return {"success": True, "path": path}
    except ClientError as e:
        logger.error(f"Failed to delete file from S3: {e}")
        return {"success": False, "error": str(e)}


def get_presigned_url(path: str, expiration: int = 3600) -> str:
    """
    Generate a presigned URL for temporary access to a file.
    
    Args:
        path: S3 key
        expiration: URL expiration time in seconds (default 1 hour)
    
    Returns:
        Presigned URL string
    """
    client = get_s3_client()
    
    try:
        url = client.generate_presigned_url(
            'get_object',
            Params={'Bucket': AWS_S3_BUCKET_NAME, 'Key': path},
            ExpiresIn=expiration
        )
        return url
    except ClientError as e:
        logger.error(f"Failed to generate presigned URL: {e}")
        raise


async def upload_machine_image(
    image_data: bytes,
    filename: str,
    vendor_id: str
) -> dict:
    """
    Upload a machine image to S3.
    
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
    Upload an RFQ drawing to S3.
    
    Args:
        drawing_data: Drawing file bytes
        filename: Original filename
        rfq_id: RFQ ID for organization
    
    Returns:
        dict with storage details
    """
    folder = f"drawings/{rfq_id}"
    return upload_file(drawing_data, filename, folder)
