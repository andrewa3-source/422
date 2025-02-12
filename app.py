from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import boto3
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(100), nullable=False)
    photos = db.relationship('Photo', backref='user', lazy=True)

class Photo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Initialize S3 client
s3_client = boto3.client('s3', 
                         aws_access_key_id=app.config['AWS_ACCESS_KEY_ID'],
                         aws_secret_access_key=app.config['AWS_SECRET_ACCESS_KEY'],
                         region_name=app.config['AWS_REGION_NAME'])

# Routes
@app.route('/')
@login_required
def gallery():
    search_query = request.args.get('search', '')
    if search_query:
        photos = Photo.query.filter(Photo.description.contains(search_query))
    else:
        photos = Photo.query.all()

    # Pass the S3 bucket name to the template
    return render_template('gallery.html', photos=photos, s3_bucket_name=app.config['S3_BUCKET_NAME'])


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('gallery'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
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
        new_user = User(username=username, password_hash=password)
        db.session.add(new_user)
        db.session.commit()
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

            # Upload to S3
            s3_client.upload_fileobj(file, app.config['S3_BUCKET_NAME'], filename)

            # Create a new photo record in the database
            new_photo = Photo(filename=filename, description=description, user_id=current_user.id)
            db.session.add(new_photo)
            db.session.commit()
            return redirect(url_for('gallery'))
    return render_template('upload.html')

@app.route('/download/<filename>')
@login_required
def download(filename):
    # Generate the download URL from S3
    file_url = s3_client.generate_presigned_url('get_object',
                                               Params={'Bucket': app.config['S3_BUCKET_NAME'], 'Key': filename},
                                               ExpiresIn=3600)  # Link expires in 1 hour
    return redirect(file_url)

@app.route('/delete/<int:photo_id>', methods=['POST'])
@login_required
def delete(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    
    # Delete the photo from S3
    try:
        s3_client.delete_object(Bucket=app.config['S3_BUCKET_NAME'], Key=photo.filename)
    except Exception as e:
        print(f"Error deleting file from S3: {e}")
    
    # Delete the photo from the database
    db.session.delete(photo)
    db.session.commit()
    
    return redirect(url_for('gallery'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create the database tables if they don't exist
    app.run(debug=False)
