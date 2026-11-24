from typing import BinaryIO

import boto3

from app.core.config import get_settings
from app.providers.storage.base import StorageProvider


class B2StorageProvider(StorageProvider):
    def __init__(self):
        settings = get_settings()
        region = settings.B2_REGION or ""
        if region.startswith("s3."):
            region = region.replace("s3.", "", 1)
        elif "s3." in region:
            region = region.split("s3.")[-1]
        self.region = region.strip() or None

        self.bucket = settings.B2_BUCKET_NAME
        self.s3_client = boto3.client(
            "s3",
            endpoint_url=settings.B2_ENDPOINT_URL,
            aws_access_key_id=settings.B2_KEY_ID,
            aws_secret_access_key=settings.B2_APPLICATION_KEY,
            region_name=self.region,
        )

    def upload_file(self, file_obj: BinaryIO, storage_key: str, content_type: str = "") -> str:
        extra_args = {}
        if content_type:
            extra_args["ContentType"] = content_type
        self.s3_client.upload_fileobj(file_obj, self.bucket, storage_key, ExtraArgs=extra_args)
        return storage_key

    def get_presigned_url(self, storage_key: str, expires_in: int = 3600) -> str:
        return self.s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": storage_key},
            ExpiresIn=expires_in,
        )

    def file_exists(self, storage_key: str) -> bool:
        try:
            self.s3_client.head_object(Bucket=self.bucket, Key=storage_key)
            return True
        except Exception:
            return False

    def download_file(self, storage_key: str) -> bytes:
        import io
        buf = io.BytesIO()
        self.s3_client.download_fileobj(self.bucket, storage_key, buf)
        return buf.getvalue()
