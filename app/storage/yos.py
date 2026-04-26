"""Yandex Object Storage client for call recordings."""

from __future__ import annotations

import boto3
from botocore.client import Config

from app.config import settings

YOS_PREFIX = "yos://"


def _client():
    return boto3.client(
        "s3",
        aws_access_key_id=settings.yos_access_key,
        aws_secret_access_key=settings.yos_secret_key,
        endpoint_url=settings.yos_endpoint,
        config=Config(signature_version="s3v4"),
        region_name="ru-central1",
    )


def upload_recording(call_db_id: int, body: bytes) -> str:
    """Залить mp3-байты в YOS под ключ recordings/{call_db_id}.mp3.

    Возвращает yos://<key> для хранения в Call.recording_url.
    """
    key = f"recordings/{call_db_id}.mp3"
    _client().put_object(
        Bucket=settings.yos_bucket,
        Key=key,
        Body=body,
        ContentType="audio/mpeg",
    )
    return f"{YOS_PREFIX}{key}"


def presign_recording(yos_uri: str, expires_seconds: int = 3600) -> str:
    """Сгенерировать temporary signed URL для скачивания mp3 из YOS."""
    key = yos_uri.removeprefix(YOS_PREFIX)
    return _client().generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.yos_bucket, "Key": key},
        ExpiresIn=expires_seconds,
    )
