from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import boto3
from config import Config
from flask import Response
from dotenv import load_dotenv
import uuid

app = Flask(__name__)
app.config.from_object(Config)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
load_dotenv()

# Initialize DynamoDB client
dynamodb = boto3.resource(
    'dynamodb',
    aws_access_key_id=app.config['AWS_ACCESS_KEY_ID'],
    aws_secret_access_key=app.config['AWS_SECRET_ACCESS_KEY'],
    region_name=app.config['AWS_REGION_NAME']
)
users_table = dynamodb.Table(app.config['DYNAMODB_USERS_TABLE'])
photos_table = dynamodb.Table(app.config['DYNAMODB_PHOTOS_TABLE'])

# Initialize S3 client
s3_client = boto3.client(
    's3',
    aws_access_key_id=app.config['AWS_ACCESS_KEY_ID'],
    aws_secret_access_key=app.config['AWS_SECRET_ACCESS_KEY'],
    region_name=app.config['AWS_REGION_NAME']
)

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, id, username, password_hash):
        self.id = id
        self.username = username
        self.password_hash = password_hash

@login_manager.user_loader
def load_user(user_id):
    response = users_table.get_item(Key={'user_id': user_id})
    user_data = response.get('Item')
    if user_data:
        return User(user_data['user_id'], user_data['username'], user_data['password_hash'])
    return None

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
@login_required
def gallery():
    search_query = request.args.get('search', '')

    # Fetch photos from the DynamoDB Photos Table
    if search_query:
        response = photos_table.scan(
            FilterExpression="contains(description, :query)",
            ExpressionAttributeValues={":query": {"S": search_query}}
        )
    else:
        response = photos_table.scan()

    photos = response.get('Items', [])

    # Enrich photos with usernames from the Users Table
    for photo in photos:
        user_id = photo['user_id']['S']  # Extract user_id from the photo entry
        user_response = users_table.get_item(
            Key={"id": {"S": user_id}}
        )
        user = user_response.get('Item', {})
        photo['username'] = user.get('username', {}).get('S', 'Unknown User')  # Default to 'Unknown User'

    # Pass enriched photos to the template
    return render_template('gallery.html', photos=photos, s3_bucket_name=app.config['S3_BUCKET_NAME'])


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('gallery'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        response = users_table.scan(
            FilterExpression="username = :username",
            ExpressionAttributeValues={":username": username}
        )
        users = response.get('Items', [])
        if users:
            user_data = users[0]
            if check_password_hash(user_data['password_hash'], password):
                user = User(user_data['user_id'], user_data['username'], user_data['password_hash'])
                login_user(user)
                return redirect(url_for('gallery'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        user_id = str(uuid.uuid4())
        users_table.put_item(Item={
            'user_id': user_id,
            'username': username,
            'password_hash': password
        })
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        file = request.files['file']
        description = request.form['description']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            s3_client.upload_fileobj(file, app.config['S3_BUCKET_NAME'], filename)
            photo_id = str(uuid.uuid4())
            photos_table.put_item(Item={
                'image_id': photo_id,
                'filename': filename,
                'description': description,
                'user_id': current_user.id
            })
            return redirect(url_for('gallery'))
    return render_template('upload.html')

@app.route('/download/<filename>')
@login_required
def download(filename):
    file_url = s3_client.generate_presigned_url(
        'get_object',
        Params={'Bucket': app.config['S3_BUCKET_NAME'], 'Key': filename},
        ExpiresIn=3600
    )
    file_object = s3_client.get_object(Bucket=app.config['S3_BUCKET_NAME'], Key=filename)
    file_data = file_object['Body'].read()
    response = Response(file_data, content_type=file_object['ContentType'])
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    return response

@app.route('/delete/<photo_id>', methods=['POST'])
@login_required
def delete(photo_id):
    response = photos_table.get_item(Key={'photo_id': photo_id})
    photo_data = response.get('Item')
    if photo_data:
        try:
            s3_client.delete_object(Bucket=app.config['S3_BUCKET_NAME'], Key=photo_data['filename'])
        except Exception as e:
            print(f"Error deleting file from S3: {e}")
        photos_table.delete_item(Key={'photo_id': photo_id})
    return redirect(url_for('gallery'))

if __name__ == '__main__':
    app.run(debug=False)
