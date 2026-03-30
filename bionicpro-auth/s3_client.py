import boto3
from botocore.exceptions import ClientError
import os

class S3Client:
    def __init__(self):
        self.endpoint = os.environ.get('S3_ENDPOINT', 'http://minio:9000')
        self.access_key = os.environ.get('S3_ACCESS_KEY', 'minioadmin')
        self.secret_key = os.environ.get('S3_SECRET_KEY', 'minioadmin')
        self.bucket = os.environ.get('S3_BUCKET', 'reports')
        self.client = boto3.client(
            's3',
            endpoint_url=self.endpoint,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            use_ssl=False,
            verify=False
        )
        self._create_bucket()

    def _create_bucket(self):
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except ClientError:
            self.client.create_bucket(Bucket=self.bucket)

    def object_exists(self, key):
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError:
            return False

    def put_object(self, key, data, content_type='text/csv'):
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
            CacheControl='public, max-age=3600'
        )

    def get_presigned_url(self, key, expires=3600):
        return self.client.generate_presigned_url(
            'get_object',
            Params={'Bucket': self.bucket, 'Key': key},
            ExpiresIn=expires
        )