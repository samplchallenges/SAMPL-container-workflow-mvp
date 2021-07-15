import os

from .base_settings import *  # lgtm [py/polluting-import]

DEBUG = False
SECRET_KEY = os.environ["SAMPL_SECRET_KEY"]
ALLOWED_HOSTS = [
    "app.samplchallenges.org",
    "samplmvp-env.eba-rhcwa63p.us-east-2.elasticbeanstalk.com",
]

DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
AWS_ACCESS_KEY_ID = os.environ["AWS_ACCESS_KEY_ID_S3"]
AWS_SECRET_ACCESS_KEY = os.environ["AWS_SECRET_ACCESS_KEY_S3"]
AWS_STORAGE_BUCKET_NAME = "sampl-league-storage"
AWS_S3_REGION_NAME = "us-east-2"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": os.environ["RDS_DB_NAME"],
        "USER": os.environ["RDS_USERNAME"],
        "PASSWORD": os.environ["RDS_PASSWORD"],
        "HOST": os.environ["RDS_HOSTNAME"],
        "PORT": os.environ["RDS_PORT"],
    }
}
