import json

# Input data (formatted as a list of dictionaries)
data = [
    {"id": "36", "filename": "blastoise.gif", "description": "BIGIG", "user_id": "1"},
    {"id": "37", "filename": "skeptical_cat.jpg", "description": "", "user_id": "3"},
    {"id": "38", "filename": "minesweeper_70.png", "description": "", "user_id": "3"},
    {"id": "41", "filename": "yin_yang_500.png", "description": "ggg", "user_id": "1"},
    {"id": "42", "filename": "311_hash_table.JPG", "description": "", "user_id": "3"},
    {"id": "43", "filename": "window.jpg", "description": "widnow", "user_id": "4"},
    {"id": "44", "filename": "guy_cries.gif", "description": "This assignment made me like this guy", "user_id": "4"},
    {"id": "45", "filename": "eel.jpg", "description": "A cool eel", "user_id": "4"},
    {"id": "46", "filename": "TRAIN.jpg", "description": "A train!", "user_id": "4"},
    {"id": "47", "filename": "incense.jpg", "description": "Incense", "user_id": "4"},
    {"id": "51", "filename": "Diagram_1.jpg", "description": "", "user_id": "6"}
]

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

# Save to JSON file
with open("images_dynamodb.json", "w") as f:
    json.dump(dynamodb_data, f, indent=4)

print("Data successfully formatted for DynamoDB batch upload!")
