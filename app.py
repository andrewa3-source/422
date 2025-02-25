import warnings
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
from pymongo import MongoClient
import certifi

# Suppress the DocumentDB compatibility warning
warnings.filterwarnings("ignore", message="You appear to be connected to a DocumentDB cluster.")

app = Flask(__name__)
app.config.from_object(Config)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
load_dotenv()

# MongoDB Connection
client = MongoClient(
    "mongodb://Blastoise:Charizard@se422documentdb.cluster-chc2qgsomjo0.us-east-2.docdb.amazonaws.com:27017",
    tls=True,
    tlsCAFile='global-bundle.pem',
    retryWrites=False
)
db = client[app.config['MONGO_DB_NAME']]  # Add this to your Config
users = db.users
photos = db.imageReferences

# Initialize S3 client (keep this for file storage)
s3_client = boto3.client(
    's3',
    aws_access_key_id=app.config['AWS_ACCESS_KEY_ID'],
    aws_secret_access_key=app.config['AWS_SECRET_ACCESS_KEY'],
    region_name=app.config['AWS_REGION_NAME']
)

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data['_id'])
        self.username = user_data['username']
        self.password_hash = user_data['password_hash']

@login_manager.user_loader
def load_user(user_id):
    user_data = users.find_one({'_id': user_id})
    if user_data:
        return User(user_data)
    return None

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
@login_required
def gallery():
    search_query = request.args.get('search', '')
    query = {'description': {'$regex': search_query, '$options': 'i'}} if search_query else {}
    photos_list = list(photos.find(query))
    
    # Enrich with usernames
    for photo in photos_list:
        user = users.find_one({'_id': photo['user_id']})
        photo['username'] = user['username'] if user else 'Unknown'
    
    return render_template('gallery.html', photos=photos_list, s3_bucket_name=app.config['S3_BUCKET_NAME'])

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('gallery'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Retrieve all users with the given username
        user_datas = users.find({'username': username})
        matched_user = None

        # Loop through each user and check the password hash
        for user_data in user_datas:
            if check_password_hash(user_data['password_hash'], password):
                matched_user = user_data
                break

        if matched_user:
            user = User(matched_user)
            login_user(user)
            return redirect(url_for('gallery'))
        else:
            # Optionally, you can flash a message or handle login errors here
            pass

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
        users.insert_one({
            '_id': user_id,
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
            photos.insert_one({
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
    photo_data = photos.find_one({'image_id': photo_id})
    if photo_data:
        try:
            s3_client.delete_object(Bucket=app.config['S3_BUCKET_NAME'], Key=photo_data['filename'])
        except Exception as e:
            print(f"Error deleting file from S3: {e}")
        photos.delete_one({'image_id': photo_id})
    return redirect(url_for('gallery'))

if __name__ == '__main__':
    app.run(debug=False)