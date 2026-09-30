import os
import boto3

class S3StorageService:
    """
    Option 1: S3 Direct Upload & Proxy Streaming
    Used for enterprise/paid tiers.
    """
    def __init__(self):
        self.bucket_name = os.getenv("AWS_S3_BUCKET", "ai-video-director-media")
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=os.getenv("AWS_REGION", "us-east-1")
        )



