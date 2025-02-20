import os
import json
import boto3
from config import Config
from dotenv import load_dotenv

load_dotenv()

# DynamoDB setup
dynamodb = boto3.client(
    'dynamodb',
    aws_access_key_id=Config.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY,
    region_name=Config.AWS_REGION_NAME
)

# Initialize DynamoDB client
dynamodb = boto3.client('dynamodb')

# Read the JSON file
with open('users.json', 'r') as json_file:
    data = json.load(json_file)

# Prepare the data for batch upload
items_to_put = []
for user in data['Users']:
    # Prepare the PutRequest for each user
    item = {
        'PutRequest': {
            'Item': {
                'user_id': {'S': user['user_id']},
                'username': {'S': user['username']},
                'password_hash': {'S': user['password_hash']}
            }
        }
    }
    items_to_put.append(item)

# Batch write the items in chunks (DynamoDB allows a max of 25 items per request)
chunks = [items_to_put[i:i + 25] for i in range(0, len(items_to_put), 25)]

# Upload in batches to DynamoDB
for chunk in chunks:
    response = dynamodb.batch_write_item(RequestItems={
        'Users': chunk  # Replace 'YourTableName' with your actual DynamoDB table name
    })
    print(f"Batch uploaded: {response}")

print("JSON data uploaded successfully!")
