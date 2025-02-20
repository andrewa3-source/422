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

# Load the JSON data from imageref.json
with open('images_dynamodb.json', 'r') as f:
    data = json.load(f)

# Convert to DynamoDB batch-write format
dynamodb_data = {
    "Images": [
        {
            "PutRequest": {
                "Item": {
                    "id": {"N": item["id"]},  # id as Number
                    "filename": {"S": item["filename"]},  # filename as String
                    "description": {"S": item["description"] if item["description"] else "N/A"},  # Handle empty descriptions
                    "user_id": {"N": item["user_id"]}  # user_id as Number
                }
            }
        }
        for item in data
    ]
}

# Save the data to a JSON file (Optional, for backup or later use)
with open("images_dynamodb.json", "w") as f:
    json.dump(dynamodb_data, f, indent=4)

# Batch write data to DynamoDB
def batch_write_to_dynamodb(data):
    for batch in data["Images"]:
        try:
            response = dynamodb.batch_write_item(RequestItems={"Images": [batch]})
            print(f"Batch Write Response: {response}")
        except Exception as e:
            print(f"Error writing to DynamoDB: {e}")

# Call the function to upload the data
batch_write_to_dynamodb(dynamodb_data)

print("Data uploaded to DynamoDB successfully.")