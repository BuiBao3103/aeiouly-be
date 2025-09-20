import os
import uuid
from typing import Optional

import boto3
from botocore.client import Config

from src.config import settings


class S3StorageService:
    def __init__(self):
        session = boto3.session.Session(
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID or None,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY or None,
            region_name=settings.AWS_S3_REGION or None,
        )
        self.s3 = session.client("s3", config=Config(s3={"addressing_style": "virtual"}))
        self.bucket = settings.AWS_S3_BUCKET
        self.public_base = settings.AWS_S3_PUBLIC_URL.strip() if settings.AWS_S3_PUBLIC_URL else ""

    def upload_fileobj(self, fileobj, content_type: str, key_prefix: str = "posts/") -> str:
        if not self.bucket:
            raise RuntimeError("AWS_S3_BUCKET is not configured")

        filename = f"{uuid.uuid4().hex}"
        ext = _guess_ext_from_content_type(content_type)
        key = f"{key_prefix}{filename}{ext}"

        self.s3.upload_fileobj(
            Fileobj=fileobj,
            Bucket=self.bucket,
            Key=key,
            ExtraArgs={
                "ContentType": content_type,
                "CacheControl": "public, max-age=31536000",
            },
        )

        if self.public_base:
            return f"{self.public_base.rstrip('/')}/{key}"
        region = settings.AWS_S3_REGION
        return f"https://{self.bucket}.s3.{region}.amazonaws.com/{key}"

    def delete_file(self, file_url: str) -> bool:
        """
        Xóa file từ S3 bucket dựa trên URL
        """
        if not self.bucket:
            raise RuntimeError("AWS_S3_BUCKET is not configured")
        
        if not file_url:
            return False
            
        try:
            # Extract key from URL
            key = self._extract_key_from_url(file_url)
            if not key:
                return False
                
            # Delete object
            self.s3.delete_object(Bucket=self.bucket, Key=key)
            return True
        except Exception as e:
            print(f"Error deleting file {file_url}: {str(e)}")
            return False

    def _extract_key_from_url(self, file_url: str) -> str:
        """
        Extract S3 key from file URL
        """
        if not file_url:
            return ""
            
        # If using custom public URL (CloudFront, etc.)
        if self.public_base and file_url.startswith(self.public_base):
            return file_url.replace(f"{self.public_base.rstrip('/')}/", "")
            
        # If using standard S3 URL
        region = settings.AWS_S3_REGION
        s3_url_pattern = f"https://{self.bucket}.s3.{region}.amazonaws.com/"
        if file_url.startswith(s3_url_pattern):
            return file_url.replace(s3_url_pattern, "")
            
        return ""


def _guess_ext_from_content_type(content_type: str) -> str:
    mapping = {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
        "image/bmp": ".bmp",
        "image/svg+xml": ".svg",
    }
    return mapping.get(content_type.lower(), "")


