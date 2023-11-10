from django.conf import settings
import boto3

AWS_REGION_NAME = settings.COGNITO_REGION
AWS_ACCESS_KEY_ID = settings.S3_CLIENT_ID
AWS_SECRET_ACCESS_KEY = settings.S3_CLIENT_SECRET
AWS_PHOTO_BUCKET = settings.SITE_PHOTOS_S3_BUCKET


class S3Interface:
    def __init__(self) -> None:
        self.__client = boto3.client(
            "s3",
            region_name=AWS_REGION_NAME,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        )

    def put_object(
        self, key: str, obj: bytes, content_type: str, bucket: str = AWS_PHOTO_BUCKET
    ) -> str:
        """Take a object and uploads it to S3 bucket returning the object id

        Args:
            key str: Unique identifier of the object in S3.
            obj bytes: object to be uploaded to S3 bucket.
            bucket (str, optional): specify the S3 bucket or use provided default. Defaults to AWS_PHOTO_BUCKET.

        Returns:
            str identifier of the object in the s3 bucket. This is the ETag parameter from response.
        """
        response = self.__client.put_object(
            Key=key,
            Body=obj,
            Bucket=bucket,
            ContentType=content_type,
            ServerSideEncryption="AES256",
            StorageClass="STANDARD",
        )
        return key

    def delete_object(
        self,
        key: str,
        bucket: str = AWS_PHOTO_BUCKET,
    ):
        response = self.__client.delete_object(Key=key, Bucket=bucket)
        return None
