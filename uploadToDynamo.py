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

# Table name
table_name = 'Images'

# Load the JSON data from images_dynamodb.json
with open('images_dynamodb.json', 'r') as f:
    data = json.load(f)

# Print data to verify the format
print("Loaded data:", data)

# Batch write data to DynamoDB
def batch_write_to_dynamodb(data):
    # Prepare the request items in the required format
    request_items = {
        table_name: [
            {
                "PutRequest": {
                    "Item": item["PutRequest"]["Item"]
                }
            }
            for item in data["Images"]
        ]
    }

    # Perform the batch write
    try:
        response = dynamodb.batch_write_item(RequestItems=request_items)
        print(f"Batch Write Response: {response}")
    except Exception as e:
        print(f"Error writing to DynamoDB: {e}")

# Call the function to upload the data
batch_write_to_dynamodb(data)

print("Data uploaded to DynamoDB successfully.")
