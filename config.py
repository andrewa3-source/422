import os
from dotenv import load_dotenv

class Config:
    load_dotenv()
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    SQLALCHEMY_DATABASE_URI = f"mysql+mysqlconnector://{os.environ['DB_USER']}:{os.environ['DB_PASSWORD']}@{os.environ['DB_HOST']}/{os.environ['DB_NAME']}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = 'static/uploads'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    AWS_REGION_NAME = 'us-east-2'  # Update this with your region
    S3_BUCKET_NAME = 'isucloudcomputingphotobucket'  # Replace with your bucket name
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp'}

     # DynamoDB Table Names
    DYNAMODB_USERS_TABLE = os.environ.get('DYNAMODB_USERS_TABLE', 'UsersTable')
    DYNAMODB_PHOTOS_TABLE = os.environ.get('DYNAMODB_PHOTOS_TABLE', 'PhotosTable')