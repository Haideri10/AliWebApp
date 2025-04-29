from flask import Flask, request, render_template_string, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from azure.storage.blob import BlobServiceClient, ContentSettings
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

app = Flask(__name__)
app.config['SECRET_KEY'] = 'f1340841002453968837b6053f9dc3fdc7fd3b7d86b87dca'

app.config[
    'SQLALCHEMY_DATABASE_URI'] = 'mssql+pyodbc://alihaider10:Haidershah10@alihaider10.database.windows.net/alihaider10?driver=ODBC+Driver+17+for+SQL+Server'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

AZURE_CONNECTION_STRING = 'DefaultEndpointsProtocol=https;AccountName=alihaider10;AccountKey=8VxYFa1SGPw2G9VU0UWG0tK73xwsYj8l6RZtZGmQRkQ9h7cTwXfazNfnq5xrW9eLc7gPe6vHjOUE+AStqS5wIA==;EndpointSuffix=core.windows.net'

AZURE_CONTAINER_NAME = 'uploads'

db = SQLAlchemy(app)
blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)
try:
    blob_service_client.create_container(AZURE_CONTAINER_NAME)
except Exception:
    pass


# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    role = db.Column(db.String(20), nullable=False)
    password = db.Column(db.String(512), nullable=False)


class Media(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    caption = db.Column(db.String(256), nullable=True)
    location = db.Column(db.String(100), nullable=True)
    people_present = db.Column(db.String(256), nullable=True)
    upload_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    file_path = db.Column(db.String(512), nullable=False)
    media_type = db.Column(db.String(20), nullable=False)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    comments = db.relationship('Comment', backref='media')
    ratings = db.relationship('Rating', backref='media')


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(500), nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    media_id = db.Column(db.Integer, db.ForeignKey('media.id'), nullable=False)


class Rating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.Integer, nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    media_id = db.Column(db.Integer, db.ForeignKey('media.id'), nullable=False)
    __table_args__ = (db.UniqueConstraint('user_id', 'media_id', name='unique_user_media_rating'),)


with app.app_context():
    db.create_all()

# Global CSS for all pages
BASE_CSS = '''
    /* Modern Dark Theme */
    :root {
        --bg-primary: #121212;
        --bg-secondary: #1e1e1e;
        --bg-card: #252525;
        --accent: #8a2be2;
        --accent-hover: #9d44ff;
        --text-primary: #ffffff;
        --text-secondary: #b3b3b3;
        --success: #4caf50;
        --error: #f44336;
        --warning: #ff9800;
    }

    * {
        box-sizing: border-box;
        margin: 0;
        padding: 0;
        font-family: 'Poppins', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }

    body {
        background-color: var(--bg-primary);
        color: var(--text-primary);
        line-height: 1.6;
        min-height: 100vh;
    }

    .container {
        max-width: 1200px;
        margin: 0 auto;
        padding: 20px;
    }

    .btn {
        display: inline-block;
        background-color: var(--accent);
        color: var(--text-primary);
        border: none;
        padding: 12px 24px;
        border-radius: 30px;
        cursor: pointer;
        font-weight: 600;
        letter-spacing: 0.5px;
        transition: all 0.3s ease;
        text-decoration: none;
        font-size: 16px;
        text-align: center;
    }

    .btn:hover {
        background-color: var(--accent-hover);
        transform: translateY(-2px);
        box-shadow: 0 10px 20px rgba(138, 43, 226, 0.2);
    }

    input, select, textarea {
        background-color: var(--bg-secondary);
        border: 2px solid #333;
        color: var(--text-primary);
        padding: 12px 16px;
        border-radius: 8px;
        margin-bottom: 16px;
        width: 100%;
        font-size: 16px;
        transition: border-color 0.3s ease;
    }

    input:focus, select:focus, textarea:focus {
        border-color: var(--accent);
        outline: none;
    }

    .card {
        background-color: var(--bg-card);
        border-radius: 16px;
        overflow: hidden;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
        margin-bottom: 30px;
        transition: transform 0.3s ease;
    }

    .card:hover {
        transform: translateY(-5px);
    }

    .card-body {
        padding: 24px;
    }

    .navbar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 20px 0;
        margin-bottom: 40px;
        border-bottom: 1px solid #333;
    }

    .navbar-brand {
        font-size: 24px;
        font-weight: 700;
        color: var(--accent);
        text-decoration: none;
    }

    .navbar-links {
        display: flex;
        gap: 20px;
    }

    .navbar-links a {
        color: var(--text-secondary);
        text-decoration: none;
        transition: color 0.3s ease;
    }

    .navbar-links a:hover {
        color: var(--accent);
    }

    .alert {
        padding: 12px 16px;
        border-radius: 8px;
        margin-bottom: 20px;
    }

    .alert-success {
        background-color: var(--success);
        color: white;
    }

    .alert-danger {
        background-color: var(--error);
        color: white;
    }

    .alert-warning {
        background-color: var(--warning);
        color: white;
    }

    /* Responsive Grid */
    .grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
        gap: 30px;
    }

    @media (max-width: 768px) {
        .grid {
            grid-template-columns: 1fr;
        }

        .navbar {
            flex-direction: column;
            gap: 15px;
        }
    }

    /* Animation Effects */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .animate-fade-in {
        animation: fadeIn 0.5s ease forwards;
    }

    /* Form Styling */
    .form-container {
        max-width: 500px;
        margin: 0 auto;
        animation: fadeIn 0.5s ease forwards;
    }

    .form-title {
        font-size: 32px;
        margin-bottom: 30px;
        text-align: center;
        font-weight: 700;
        background: linear-gradient(to right, var(--accent), var(--accent-hover));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .form-group {
        margin-bottom: 20px;
    }

    .form-label {
        display: block;
        margin-bottom: 8px;
        font-weight: 500;
        color: var(--text-secondary);
    }

    /* Media Cards */
    .media-title {
        font-size: 24px;
        margin-bottom: 12px;
        color: var(--text-primary);
    }

    .media-caption {
        color: var(--text-secondary);
        margin-bottom: 16px;
    }

    .media-meta {
        display: flex;
        gap: 16px;
        margin-bottom: 16px;
        font-size: 14px;
        color: var(--text-secondary);
    }

    .media-meta span {
        display: flex;
        align-items: center;
        gap: 5px;
    }

    .media-content {
        width: 100%;
        margin-bottom: 20px;
        border-radius: 12px;
        overflow: hidden;
    }

    .actions-container {
        margin-top: 20px;
        border-top: 1px solid #333;
        padding-top: 20px;
    }

    .rating-container {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 20px;
    }

    .rating-stars {
        display: inline-flex;
        gap: 2px;
        font-size: 20px;
        color: #ffc107;
    }

    .comments-section {
        margin-top: 20px;
    }

    .comment-item {
        padding: 12px 16px;
        background-color: var(--bg-secondary);
        border-radius: 8px;
        margin-bottom: 12px;
    }

    .star-rating {
        display: flex;
        flex-direction: row-reverse;
        gap: 8px;
    }

    .star-rating input {
        display: none;
    }

    .star-rating label {
        cursor: pointer;
        width: 30px;
        height: 30px;
        background-color: var(--bg-secondary);
        border-radius: 50%;
        display: flex;
        justify-content: center;
        align-items: center;
        color: #ccc;
        font-size: 20px;
        transition: all 0.2s ease;
    }

    .star-rating label:hover,
    .star-rating label:hover ~ label,
    .star-rating input:checked ~ label {
        color: #ffc107;
    }
'''


# Routes
@app.route('/')
def index():
    return render_template_string('''
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>MediaVerse</title>
            <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
            <style>
                ''' + BASE_CSS + '''
                .hero {
                    height: 100vh;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    align-items: center;
                    text-align: center;
                    padding: 0 20px;
                }

                .hero-title {
                    font-size: 5rem;
                    margin-bottom: 20px;
                    font-weight: 700;
                    background: linear-gradient(to right, var(--accent), var(--accent-hover));
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    animation: fadeIn 0.8s ease forwards;
                }

                .hero-subtitle {
                    font-size: 1.5rem;
                    margin-bottom: 40px;
                    color: var(--text-secondary);
                    max-width: 700px;
                    animation: fadeIn 1s ease forwards;
                }

                .hero-buttons {
                    display: flex;
                    gap: 20px;
                    animation: fadeIn 1.2s ease forwards;
                }

                .hero-shape {
                    position: absolute;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    overflow: hidden;
                    z-index: -1;
                }

                .blob-1, .blob-2 {
                    position: absolute;
                    filter: blur(50px);
                    opacity: 0.15;
                }

                .blob-1 {
                    width: 600px;
                    height: 600px;
                    background: var(--accent);
                    top: -200px;
                    right: -200px;
                    border-radius: 50%;
                }

                .blob-2 {
                    width: 400px;
                    height: 400px;
                    background: #4158D0;
                    bottom: -150px;
                    left: -150px;
                    border-radius: 30% 70% 70% 30% / 30% 30% 70% 70%;
                }

                .btn-secondary {
                    background: transparent;
                    border: 2px solid var(--accent);
                }

                .btn-secondary:hover {
                    background: rgba(138, 43, 226, 0.1);
                }
            </style>
        </head>
        <body>
            <div class="hero-shape">
                <div class="blob-1"></div>
                <div class="blob-2"></div>
            </div>

            <div class="hero">
                <h1 class="hero-title">MediaVerse</h1>
                <p class="hero-subtitle">Share and discover amazing videos and pictures. Join our creative community today!</p>
                <div class="hero-buttons">
                    <a href="{{ url_for('login') }}" class="btn">Log In</a>
                    <a href="{{ url_for('register') }}" class="btn btn-secondary">Sign Up</a>
                </div>
            </div>
        </body>
        </html>
    ''')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        hashed_password = generate_password_hash(password)
        user = User(username=username, email=email, role=role, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template_string('''
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Register - MediaVerse</title>
            <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
            <style>
                ''' + BASE_CSS + '''
                .auth-container {
                    display: flex;
                    min-height: 100vh;
                }

                .auth-image {
                    flex: 1;
                    background-image: url('https://images.unsplash.com/photo-1550745165-9bc0b252726f');
                    background-size: cover;
                    background-position: center;
                    position: relative;
                    display: none;
                }

                @media (min-width: 768px) {
                    .auth-image {
                        display: block;
                    }
                }

                .auth-image::after {
                    content: "";
                    position: absolute;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: rgba(0, 0, 0, 0.5);
                }

                .auth-form {
                    flex: 1;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    padding: 40px;
                }

                .auth-logo {
                    font-size: 24px;
                    font-weight: 700;
                    margin-bottom: 40px;
                    color: var(--accent);
                }

                .auth-title {
                    font-size: 32px;
                    margin-bottom: 10px;
                }

                .auth-subtitle {
                    color: var(--text-secondary);
                    margin-bottom: 30px;
                }

                .role-selector {
                    display: flex;
                    gap: 20px;
                    margin-bottom: 20px;
                }

                .role-option {
                    flex: 1;
                    position: relative;
                }

                .role-option input {
                    position: absolute;
                    opacity: 0;
                    cursor: pointer;
                }

                .role-option label {
                    display: block;
                    background-color: var(--bg-secondary);
                    padding: 20px;
                    border-radius: 12px;
                    text-align: center;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    border: 2px solid transparent;
                }

                .role-option input:checked + label {
                    border-color: var(--accent);
                    background-color: rgba(138, 43, 226, 0.1);
                }

                .role-title {
                    font-weight: 600;
                    margin-bottom: 8px;
                }

                .role-desc {
                    font-size: 14px;
                    color: var(--text-secondary);
                }

                .auth-footer {
                    margin-top: 30px;
                    text-align: center;
                    color: var(--text-secondary);
                }

                .auth-footer a {
                    color: var(--accent);
                    text-decoration: none;
                }
            </style>
        </head>
        <body>
            <div class="auth-container">
                <div class="auth-image"></div>
                <div class="auth-form">
                    <div class="auth-logo">MediaVerse</div>

                    <h1 class="auth-title">Create an Account</h1>
                    <p class="auth-subtitle">Join our creative community today!</p>

                    <form method="POST" action="{{ url_for('register') }}">
                        <div class="form-group">
                            <label class="form-label">Username</label>
                            <input type="text" name="username" placeholder="Choose a username" required>
                        </div>

                        <div class="form-group">
                            <label class="form-label">Email</label>
                            <input type="email" name="email" placeholder="Your email address" required>
                        </div>

                        <div class="form-group">
                            <label class="form-label">Password</label>
                            <input type="password" name="password" placeholder="Create a password" required>
                        </div>

                        <div class="form-group">
                            <label class="form-label">Account Type</label>
                            <div class="role-selector">
                                <div class="role-option">
                                    <input type="radio" id="creator" name="role" value="creator" checked>
                                    <label for="creator">
                                        <div class="role-title">Creator</div>
                                        <div class="role-desc">Upload and share your content</div>
                                    </label>
                                </div>
                                <div class="role-option">
                                    <input type="radio" id="consumer" name="role" value="consumer">
                                    <label for="consumer">
                                        <div class="role-title">Consumer</div>
                                        <div class="role-desc">Discover and enjoy content</div>
                                    </label>
                                </div>
                            </div>
                        </div>

                        <button type="submit" class="btn">Create Account</button>
                    </form>

                    <div class="auth-footer">
                        Already have an account? <a href="{{ url_for('login') }}">Log In</a>
                    </div>
                </div>
            </div>
        </body>
        </html>
    ''')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['role'] = user.role
            flash('Welcome back!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password. Please try again.', 'danger')
    return render_template_string('''
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Login - MediaVerse</title>
            <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
            <style>
                ''' + BASE_CSS + '''
                .auth-container {
                    display: flex;
                    min-height: 100vh;
                }

                .auth-image {
                    flex: 1;
                    background-image: url('https://images.unsplash.com/photo-1536240478700-b869070f9279');
                    background-size: cover;
                    background-position: center;
                    position: relative;
                    display: none;
                }

                @media (min-width: 768px) {
                    .auth-image {
                        display: block;
                    }
                }

                .auth-image::after {
                    content: "";
                    position: absolute;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: rgba(0, 0, 0, 0.5);
                }

                .auth-form {
                    flex: 1;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    padding: 40px;
                }

                .auth-logo {
                    font-size: 24px;
                    font-weight: 700;
                    margin-bottom: 40px;
                    color: var(--accent);
                }

                .auth-title {
                    font-size: 32px;
                    margin-bottom: 10px;
                }

                .auth-subtitle {
                    color: var(--text-secondary);
                    margin-bottom: 30px;
                }

                .auth-footer {
                    margin-top: 30px;
                    text-align: center;
                    color: var(--text-secondary);
                }

                .auth-footer a {
                    color: var(--accent);
                    text-decoration: none;
                }

                .flash-message {
                    padding: 15px;
                    border-radius: 8px;
                    margin-bottom: 20px;
                }

                .flash-success {
                    background-color: var(--success);
                }

                .flash-danger {
                    background-color: var(--error);
                }
            </style>
        </head>
        <body>
            <div class="auth-container">
                <div class="auth-image"></div>
                <div class="auth-form">
                    <div class="auth-logo">MediaVerse</div>

                    <h1 class="auth-title">Welcome Back</h1>
                    <p class="auth-subtitle">Log in to your account to continue</p>

                    {% with messages = get_flashed_messages(with_categories=true) %}
                        {% if messages %}
                            {% for category, message in messages %}
                                <div class="flash-message flash-{{ category }}">
                                    {{ message }}
                                </div>
                            {% endfor %}
                        {% endif %}
                    {% endwith %}

                    <form method="POST" action="{{ url_for('login') }}">
                        <div class="form-group">
                            <label class="form-label">Username</label>
                            <input type="text" name="username" placeholder="Your username" required>
                        </div>

                        <div class="form-group">
                            <label class="form-label">Password</label>
                            <input type="password" name="password" placeholder="Your password" required>
                        </div>

                        <button type="submit" class="btn">Log In</button>
                    </form>

                    <div class="auth-footer">
                        Don't have an account? <a href="{{ url_for('register') }}">Sign Up</a>
                    </div>
                </div>
            </div>
        </body>
        </html>
    ''')


@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    search_query = request.form.get('search_query', '')
    media = Media.query.filter(Media.title.contains(search_query)).options(
        joinedload(Media.comments),
        joinedload(Media.ratings)
    ).all()

    if session['role'] == 'creator':
        return render_template_string('''
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Creator Dashboard - MediaVerse</title>
                <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
                <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
                <style>
                    ''' + BASE_CSS + '''
                    .dashboard {
                        display: flex;
                        min-height: 100vh;
                    }

                    .sidebar {
                        width: 260px;
                        background-color: var(--bg-secondary);
                        padding: 20px;
                        transition: all 0.3s ease;
                    }

                    .sidebar-logo {
                        font-size: 24px;
                        font-weight: 700;
                        color: var(--accent);
                        margin-bottom: 40px;
                        display: flex;
                        align-items: center;
                        gap: 10px;
                    }

                    .sidebar-menu {
                        display: flex;
                        flex-direction: column;
                        gap: 5px;
                    }

                    .sidebar-link {
                        display: flex;
                        align-items: center;
                        gap: 12px;
                        padding: 12px 15px;
                        border-radius: 8px;
                        color: var(--text-secondary);
                        text-decoration: none;
                        transition: all 0.3s ease;
                    }

                    .sidebar-link:hover, .sidebar-link.active {
                        background-color: var(--accent);
                        color: white;
                    }

                    .sidebar-link i {
                        font-size: 18px;
                        width: 24px;
                        text-align: center;
                    }

                    .main-content {
                        flex: 1;
                        padding: 30px;
                        background-color: var(--bg-primary);
                    }

                    .dashboard-header {
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        margin-bottom: 30px;
                    }

                    .dashboard-title {
                        font-size: 24px;
                        font-weight: 700;
                    }

                    .user-profile {
                        display: flex;
                        align-items: center;
                        gap: 10px;
                    }

                    .user-avatar {
                        width: 40px;
                        height: 40px;
                        border-radius: 50%;
                        background-color: var(--accent);
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        font-weight: 600;
                        color: white;
                    }
        .user-name {
                                font-weight: 500;
                            }

                            .panel {
                                background-color: var(--bg-card);
                                border-radius: 16px;
                                padding: 30px;
                                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
                                margin-bottom: 30px;
                            }

                            .panel-title {
                                font-size: 20px;
                                margin-bottom: 20px;
                                font-weight: 600;
                            }

                            .upload-container {
                                border: 2px dashed #444;
                                border-radius: 12px;
                                padding: 40px;
                                text-align: center;
                                transition: all 0.3s ease;
                                cursor: pointer;
                            }

                            .upload-container:hover {
                                border-color: var(--accent);
                            }

                            .upload-icon {
                                font-size: 48px;
                                color: var(--accent);
                                margin-bottom: 20px;
                            }

                            .upload-text {
                                margin-bottom: 20px;
                                color: var(--text-secondary);
                            }

                            .file-input {
                                display: none;
                            }

                            #dropzone {
                                min-height: 200px;
                                display: flex;
                                flex-direction: column;
                                justify-content: center;
                                align-items: center;
                            }

                            .flash-message {
                                padding: 15px;
                                border-radius: 8px;
                                margin-bottom: 20px;
                            }

                            .flash-success {
                                background-color: var(--success);
                            }

                            .flash-danger {
                                background-color: var(--error);
                            }
                        </style>
                    </head>
                    <body>
                        <div class="dashboard">
                            <div class="sidebar">
                                <div class="sidebar-logo">
                                    <i class="fas fa-photo-film"></i>
                                    MediaVerse
                                </div>

                                <nav class="sidebar-menu">
                                    <a href="{{ url_for('dashboard') }}" class="sidebar-link active">
                                        <i class="fas fa-home"></i>
                                        Dashboard
                                    </a>
                                    <a href="#" class="sidebar-link">
                                        <i class="fas fa-photo-film"></i>
                                        My Media
                                    </a>
                                    <a href="#" class="sidebar-link">
                                        <i class="fas fa-chart-bar"></i>
                                        Analytics
                                    </a>
                                    <a href="#" class="sidebar-link">
                                        <i class="fas fa-comment"></i>
                                        Comments
                                    </a>
                                    <a href="#" class="sidebar-link">
                                        <i class="fas fa-cog"></i>
                                        Settings
                                    </a>
                                    <a href="{{ url_for('logout') }}" class="sidebar-link">
                                        <i class="fas fa-sign-out-alt"></i>
                                        Logout
                                    </a>
                                </nav>
                            </div>

                            <div class="main-content">
                                <div class="dashboard-header">
                                    <h1 class="dashboard-title">Creator Dashboard</h1>
                                    <div class="user-profile">
                                        <div class="user-avatar">
                                            {{ session.username[0] if session.username else 'U' }}
                                        </div>
                                        <span class="user-name">Creator</span>
                                    </div>
                                </div>

                                {% with messages = get_flashed_messages(with_categories=true) %}
                                    {% if messages %}
                                        {% for category, message in messages %}
                                            <div class="flash-message flash-{{ category }}">
                                                {{ message }}
                                            </div>
                                        {% endfor %}
                                    {% endif %}
                                {% endwith %}

                                <div class="panel">
                                    <h2 class="panel-title">Upload New Media</h2>

                                    <form method="POST" action="{{ url_for('upload') }}" enctype="multipart/form-data">
                                        <div class="form-group">
                                            <label class="form-label">Title</label>
                                            <input type="text" name="title" placeholder="Give your media a title" required>
                                        </div>

                                        <div class="form-group">
                                            <label class="form-label">Caption</label>
                                            <textarea name="caption" placeholder="Add a caption to describe your media" rows="3"></textarea>
                                        </div>

                                        <div class="form-group">
                                            <label class="form-label">Location</label>
                                            <input type="text" name="location" placeholder="Where was this taken?">
                                        </div>

                                        <div class="form-group">
                                            <label class="form-label">People Present</label>
                                            <input type="text" name="people_present" placeholder="Who's in this media?">
                                        </div>

                                        <div class="form-group">
                                            <label class="form-label">Media Type</label>
                                            <select name="media_type" required>
                                                <option value="video">Video</option>
                                                <option value="picture">Picture</option>
                                            </select>
                                        </div>

                                        <div class="form-group">
                                            <label class="form-label">File</label>
                                            <div class="upload-container" id="dropzone" onclick="document.getElementById('file-input').click()">
                                                <i class="fas fa-cloud-upload-alt upload-icon"></i>
                                                <p class="upload-text">Drag & drop your file here or click to browse</p>
                                                <input type="file" name="file" id="file-input" class="file-input" required>
                                                <p id="selected-file">No file selected</p>
                                            </div>
                                        </div>

                                        <button type="submit" class="btn">Upload Media</button>
                                    </form>
                                </div>
                            </div>
                        </div>

                        <script>
                            const fileInput = document.getElementById('file-input');
                            const selectedFile = document.getElementById('selected-file');

                            fileInput.addEventListener('change', function() {
                                if(fileInput.files.length > 0) {
                                    selectedFile.textContent = fileInput.files[0].name;
                                } else {
                                    selectedFile.textContent = 'No file selected';
                                }
                            });

                            const dropzone = document.getElementById('dropzone');

                            ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
                                dropzone.addEventListener(eventName, preventDefaults, false);
                            });

                            function preventDefaults(e) {
                                e.preventDefault();
                                e.stopPropagation();
                            }

                            ['dragenter', 'dragover'].forEach(eventName => {
                                dropzone.addEventListener(eventName, highlight, false);
                            });

                            ['dragleave', 'drop'].forEach(eventName => {
                                dropzone.addEventListener(eventName, unhighlight, false);
                            });

                            function highlight() {
                                dropzone.style.borderColor = 'var(--accent)';
                                dropzone.style.backgroundColor = 'rgba(138, 43, 226, 0.1)';
                            }

                            function unhighlight() {
                                dropzone.style.borderColor = '#444';
                                dropzone.style.backgroundColor = 'transparent';
                            }

                            dropzone.addEventListener('drop', handleDrop, false);

                            function handleDrop(e) {
                                const dt = e.dataTransfer;
                                const files = dt.files;
                                fileInput.files = files;

                                if(files.length > 0) {
                                    selectedFile.textContent = files[0].name;
                                }
                            }
                        </script>
                    </body>
                    </html>
                ''')

    else:  # Consumer view
        return render_template_string('''
                    <!DOCTYPE html>
                    <html lang="en">
                    <head>
                        <meta charset="UTF-8">
                        <meta name="viewport" content="width=device-width, initial-scale=1.0">
                        <title>Discover Media - MediaVerse</title>
                        <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
                        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
                        <style>
                            ''' + BASE_CSS + '''
                            .header {
                                padding: 20px 0;
                                background-color: var(--bg-secondary);
                            }

                            .header-container {
                                max-width: 1200px;
                                margin: 0 auto;
                                padding: 0 20px;
                                display: flex;
                                justify-content: space-between;
                                align-items: center;
                            }

                            .logo {
                                font-size: 24px;
                                font-weight: 700;
                                color: var(--accent);
                                text-decoration: none;
                                display: flex;
                                align-items: center;
                                gap: 10px;
                            }

                            .nav-links {
                                display: flex;
                                gap: 20px;
                            }

                            .nav-link {
                                color: var(--text-secondary);
                                text-decoration: none;
                                transition: color 0.3s ease;
                                display: flex;
                                align-items: center;
                                gap: 5px;
                            }

                            .nav-link:hover, .nav-link.active {
                                color: var(--accent);
                            }

                            .search-container {
                                max-width: 1200px;
                                margin: 30px auto;
                                padding: 0 20px;
                            }

                            .search-form {
                                display: flex;
                                gap: 10px;
                            }

                            .search-input {
                                flex: 1;
                                padding: 12px 20px;
                                border-radius: 30px;
                                border: none;
                                background-color: var(--bg-secondary);
                                color: var(--text-primary);
                                font-size: 16px;
                            }

                            .search-btn {
                                background-color: var(--accent);
                                color: white;
                                border: none;
                                border-radius: 30px;
                                padding: 0 25px;
                                cursor: pointer;
                                transition: all 0.3s ease;
                            }

                            .search-btn:hover {
                                background-color: var(--accent-hover);
                            }

                            .media-grid {
                                max-width: 1200px;
                                margin: 0 auto;
                                padding: 0 20px;
                                display: grid;
                                grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                                gap: 30px;
                            }

                            .media-item {
                                background-color: var(--bg-card);
                                border-radius: 16px;
                                overflow: hidden;
                                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
                                transition: transform 0.3s ease;
                            }

                            .media-item:hover {
                                transform: translateY(-10px);
                            }

                            .media-preview {
                                width: 100%;
                                aspect-ratio: 16/9;
                                object-fit: cover;
                            }

                            .media-info {
                                padding: 20px;
                            }

                            .media-title {
                                font-size: 18px;
                                font-weight: 600;
                                margin-bottom: 8px;
                                color: var(--text-primary);
                            }

                            .media-caption {
                                color: var(--text-secondary);
                                font-size: 14px;
                                margin-bottom: 15px;
                            }

                            .media-meta {
                                display: flex;
                                justify-content: space-between;
                                color: var(--text-secondary);
                                font-size: 12px;
                            }

                            .modal {
                                display: none;
                                position: fixed;
                                top: 0;
                                left: 0;
                                width: 100%;
                                height: 100%;
                                background-color: rgba(0, 0, 0, 0.8);
                                z-index: 1000;
                                overflow-y: auto;
                            }

                            .modal-content {
                                background-color: var(--bg-card);
                                margin: 50px auto;
                                max-width: 900px;
                                border-radius: 16px;
                                overflow: hidden;
                                animation: modalFadeIn 0.3s ease;
                            }

                            @keyframes modalFadeIn {
                                from { opacity: 0; transform: translateY(-50px); }
                                to { opacity: 1; transform: translateY(0); }
                            }

                            .modal-header {
                                display: flex;
                                justify-content: space-between;
                                align-items: center;
                                padding: 20px;
                                border-bottom: 1px solid #333;
                            }

                            .modal-title {
                                font-size: 24px;
                                font-weight: 600;
                            }

                            .modal-close {
                                background: none;
                                border: none;
                                color: var(--text-secondary);
                                font-size: 24px;
                                cursor: pointer;
                            }

                            .modal-body {
                                padding: 20px;
                            }

                            .modal-media {
                                width: 100%;
                                max-height: 500px;
                                object-fit: contain;
                                border-radius: 12px;
                                margin-bottom: 20px;
                            }

                            .modal-caption {
                                color: var(--text-secondary);
                                margin-bottom: 20px;
                            }

                            .modal-metadata {
                                display: flex;
                                gap: 15px;
                                color: var(--text-secondary);
                                margin-bottom: 20px;
                            }

                            .interaction-bar {
                                display: flex;
                                gap: 20px;
                                margin-top: 20px;
                                padding-top: 20px;
                                border-top: 1px solid #333;
                            }

                            .rating-form {
                                display: flex;
                                align-items: center;
                                gap: 10px;
                            }

                            .comments-section {
                                margin-top: 30px;
                            }

                            .comment-form {
                                display: flex;
                                gap: 10px;
                                margin-bottom: 20px;
                            }

                            .comment-input {
                                flex: 1;
                            }

                            .comment {
                                background-color: var(--bg-secondary);
                                padding: 15px;
                                border-radius: 12px;
                                margin-bottom: 15px;
                            }

                            .comment-meta {
                                display: flex;
                                justify-content: space-between;
                                color: var(--text-secondary);
                                font-size: 12px;
                                margin-bottom: 8px;
                            }

                            .avg-rating {
                                display: flex;
                                align-items: center;
                                gap: 5px;
                            }

                            .stars {
                                color: #ffc107;
                            }

                            .no-results {
                                text-align: center;
                                padding: 50px 0;
                                color: var(--text-secondary);
                            }

                            .flash-message {
                                max-width: 1200px;
                                margin: 20px auto;
                                padding: 15px 20px;
                                border-radius: 8px;
                            }

                            .flash-success {
                                background-color: var(--success);
                            }

                            .flash-danger {
                                background-color: var(--error);
                            }
                        </style>
                    </head>
                    <body>
                        <header class="header">
                            <div class="header-container">
                                <a href="{{ url_for('dashboard') }}" class="logo">
                                    <i class="fas fa-photo-film"></i>
                                    MediaVerse
                                </a>
                                <nav class="nav-links">
                                    <a href="{{ url_for('dashboard') }}" class="nav-link active">
                                        <i class="fas fa-compass"></i> Discover
                                    </a>
                                    <a href="#" class="nav-link">
                                        <i class="fas fa-fire"></i> Trending
                                    </a>
                                    <a href="#" class="nav-link">
                                        <i class="fas fa-bookmark"></i> Saved
                                    </a>
                                    <a href="{{ url_for('logout') }}" class="nav-link">
                                        <i class="fas fa-sign-out-alt"></i> Logout
                                    </a>
                                </nav>
                            </div>
                        </header>

                    <div class="search-container">
                        {% with messages = get_flashed_messages(with_categories=true) %}
                            {% if messages %}
                                {% for category, message in messages %}
                                    <div class="flash-message flash-{{ category }}">
                                        {{ message }}
                                    </div>
                                {% endfor %}
                            {% endif %}
                        {% endwith %}

                        <form class="search-form" method="POST" action="{{ url_for('dashboard') }}">
                            <input type="text" name="search_query" placeholder="Search for media..." class="search-input" value="{{ request.form.get('search_query', '') }}">
                            <button type="submit" class="search-btn">Search</button>
                        </form>
                    </div>

                    <div class="media-grid">
                        {% if media %}
                            {% for item in media %}
                                <div class="media-item" onclick="openModal({{ item.id }})">
                                    {% if item.media_type == 'video' %}
                                        <video class="media-preview" poster="{{ item.file_path }}?format=jpg">
                                            <source src="{{ item.file_path }}" type="video/mp4">
                                        </video>
                                    {% else %}
                                        <img src="{{ item.file_path }}" alt="{{ item.title }}" class="media-preview">
                                    {% endif %}
                                    <div class="media-info">
                                        <h3 class="media-title">{{ item.title | e }}</h3>
                                        <p class="media-caption">{{ item.caption | e }}</p>
                                        <div class="media-meta">
                                            <div class="avg-rating">
                                                <i class="fas fa-star stars"></i>
                                                {% set rating_sum = namespace(value=0) %}
                                                {% for rating in item.ratings %}
                                                    {% set rating_sum.value = rating_sum.value + rating.value %}
                                                {% endfor %}
                                                {% if item.ratings|length > 0 %}
                                                    {{ (rating_sum.value / item.ratings|length) | round(1) }}
                                                {% else %}
                                                    No ratings
                                                {% endif %}
                                            </div>
                                            <span>{{ item.comments|length }} comments</span>
                                        </div>
                                    </div>
                                </div>

                                <!-- Modal for this media item -->
                                <div id="modal-{{ item.id }}" class="modal">
                                    <div class="modal-content">
                                        <div class="modal-header">
                                            <h2 class="modal-title">{{ item.title | e }}</h2>
                                            <button class="modal-close" onclick="closeModal({{ item.id }})">×</button>
                                        </div>
                                        <div class="modal-body">
                                            {% if item.media_type == 'video' %}
                                                <video class="modal-media" controls>
                                                    <source src="{{ item.file_path }}" type="video/mp4">
                                                    Your browser does not support video playback.
                                                </video>
                                            {% else %}
                                                <img src="{{ item.file_path }}" alt="{{ item.title }}" class="modal-media">
                                            {% endif %}
                                            <p class="modal-caption">{{ item.caption | e }}</p>
                                            <div class="modal-metadata">
                                                {% if item.location %}
                                                    <div>
                                                        <i class="fas fa-map-marker-alt"></i> {{ item.location | e }}
                                                    </div>
                                                {% endif %}
                                                {% if item.people_present %}
                                                    <div>
                                                        <i class="fas fa-users"></i> {{ item.people_present | e }}
                                                    </div>
                                                {% endif %}
                                                <div>
                                                    <i class="fas fa-calendar"></i> {{ item.upload_date.strftime('%B %d, %Y') }}
                                                </div>
                                            </div>

                                            <div class="interaction-bar">
                                                <form class="rating-form" method="POST" action="{{ url_for('rate') }}">
                                                    <input type="hidden" name="media_id" value="{{ item.id }}">
                                                    <select name="value" required>
                                                        <option value="">Rate this</option>
                                                        <option value="1">1 - Poor</option>
                                                        <option value="2">2 - Fair</option>
                                                        <option value="3">3 - Good</option>
                                                        <option value="4">4 - Very Good</option>
                                                        <option value="5">5 - Excellent</option>
                                                    </select>
                                                    <button type="submit" class="btn">Rate</button>
                                                </form>
                                            </div>

                                            <div class="comments-section">
                                                <h3>Comments ({{ item.comments|length }})</h3>
                                                <form class="comment-form" method="POST" action="{{ url_for('comment') }}">
                                                    <input type="hidden" name="media_id" value="{{ item.id }}">
                                                    <input type="text" name="text" placeholder="Add a comment..." class="comment-input" required>
                                                    <button type="submit" class="btn">Post</button>
                                                </form>

                                                {% if item.comments %}
                                                    {% for comment in item.comments %}
                                                        <div class="comment">
                                                            <div class="comment-meta">
                                                                <span>User #{{ comment.user_id }}</span>
                                                                <span>{{ comment.date.strftime('%B %d, %Y') }}</span>
                                                            </div>
                                                            <p>{{ comment.text | e }}</p>
                                                        </div>
                                                    {% endfor %}
                                                {% else %}
                                                    <p>No comments yet. Be the first to comment!</p>
                                                {% endif %}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            {% endfor %}
                        {% else %}
                            <div class="no-results">
                                <i class="fas fa-search" style="font-size: 48px; margin-bottom: 20px;"></i>
                                <h2>No results found</h2>
                                <p>Try searching with different keywords</p>
                            </div>
                        {% endif %}
                    </div>

                    <script>
                        function openModal(id) {
                            document.getElementById('modal-' + id).style.display = "block";
                            document.body.style.overflow = "hidden";
                        }

                        function closeModal(id) {
                            document.getElementById('modal-' + id).style.display = "none";
                            document.body.style.overflow = "auto";
                        }

                        // Close modal when clicking outside the content
                        window.onclick = function(event) {
                            if (event.target.classList.contains('modal')) {
                                event.target.style.display = "none";
                                document.body.style.overflow = "auto";
                            }
                        }
                    </script>
                </body>
                </html>
            ''', media=media)


@app.route('/upload', methods=['POST'])
def upload():
    if 'user_id' not in session or session['role'] != 'creator':
        return redirect(url_for('login'))

    title = request.form['title']
    caption = request.form['caption']
    location = request.form['location']
    people_present = request.form['people_present']
    file = request.files['file']
    media_type = request.form['media_type']

    if file:
        filename = file.filename
        blob_client = blob_service_client.get_blob_client(container=AZURE_CONTAINER_NAME, blob=filename)
        blob_client.upload_blob(file, overwrite=True, content_settings=ContentSettings(
            content_type='video/mp4' if media_type == 'video' else 'image/jpeg'))
        blob_url = f"https://{blob_service_client.account_name}.blob.core.windows.net/{AZURE_CONTAINER_NAME}/{filename}"

        media = Media(
            title=title,
            caption=caption,
            location=location,
            people_present=people_present,
            file_path=blob_url,
            media_type=media_type,
            creator_id=session['user_id']
        )
        db.session.add(media)
        db.session.commit()
        flash('Media uploaded successfully!', 'success')
    else:
        flash('No file selected!', 'danger')

    return redirect(url_for('dashboard'))


@app.route('/comment', methods=['POST'])
def comment():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    text = request.form['text']
    media_id = request.form['media_id']

    comment = Comment(
        text=text,
        user_id=session['user_id'],
        media_id=media_id
    )
    db.session.add(comment)
    db.session.commit()
    flash('Comment added!', 'success')

    return redirect(url_for('dashboard'))


@app.route('/rate', methods=['POST'])
def rate():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    media_id = request.form['media_id']
    value = request.form['value']

    existing_rating = Rating.query.filter_by(user_id=session['user_id'], media_id=media_id).first()
    if existing_rating:
        flash('You have already rated this media!', 'warning')
        return redirect(url_for('dashboard'))

    rating = Rating(
        value=value,
        user_id=session['user_id'],
        media_id=media_id
    )
    db.session.add(rating)
    db.session.commit()
    flash('Media rated!', 'success')

    return redirect(url_for('dashboard'))


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('role', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))


if __name__ == "__main__":
    app.run()
