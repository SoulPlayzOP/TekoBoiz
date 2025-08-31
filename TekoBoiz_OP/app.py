from flask import Flask, render_template, request, redirect, url_for, jsonify, session
import os
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-change-this')

ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'madhavbatra251@gmail.com')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'mdv251@123')

# Initialize Firebase
db = None
try:
    if os.path.exists('firebase-key.json'):
        # Local development with service account file
        cred = credentials.Certificate('firebase-key.json')
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("Firebase initialized successfully")
    elif os.getenv('FIREBASE_PRIVATE_KEY'):
        # Production with environment variables
        cred = credentials.Certificate({
            "type": "service_account",
            "project_id": os.getenv('FIREBASE_PROJECT_ID', 'tekoboiz'),
            "private_key_id": os.getenv('FIREBASE_PRIVATE_KEY_ID'),
            "private_key": os.getenv('FIREBASE_PRIVATE_KEY', '').replace('\\n', '\n'),
            "client_email": os.getenv('FIREBASE_CLIENT_EMAIL'),
            "client_id": os.getenv('FIREBASE_CLIENT_ID'),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token"
        })
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("Firebase initialized with environment variables")
except Exception as e:
    print(f"Firebase not initialized: {e}")
    print("Falling back to JSON files")
    db = None

def load_tutorials():
    if db:
        try:
            docs = db.collection('tutorials').order_by('id').get()
            return [doc.to_dict() for doc in docs]
        except:
            return []
    else:
        # Fallback to JSON file
        import json
        if os.path.exists('tutorials.json'):
            with open('tutorials.json', 'r') as f:
                return json.load(f)
        return []

def load_videos():
    if db:
        try:
            docs = db.collection('latest_videos').order_by('id').get()
            return [doc.to_dict() for doc in docs]
        except:
            return []
    else:
        # Fallback to JSON file
        import json
        if os.path.exists('latest_videos.json'):
            with open('latest_videos.json', 'r') as f:
                return json.load(f)
        return []

def save_tutorial(tutorial):
    if db:
        try:
            db.collection('tutorials').add(tutorial)
            return True
        except:
            return False
    else:
        # Fallback to JSON file
        import json
        tutorials = load_tutorials()
        tutorials.append(tutorial)
        with open('tutorials.json', 'w') as f:
            json.dump(tutorials, f, indent=2)
        return True

def save_video(video):
    if db:
        try:
            db.collection('latest_videos').add(video)
            return True
        except:
            return False
    else:
        # Fallback to JSON file
        import json
        videos = load_videos()
        videos.append(video)
        with open('latest_videos.json', 'w') as f:
            json.dump(videos, f, indent=2)
        return True

def delete_tutorial_by_id(tutorial_id):
    try:
        docs = db.collection('tutorials').where('id', '==', tutorial_id).get()
        for doc in docs:
            doc.reference.delete()
        return True
    except:
        return False

def delete_video_by_id(video_id):
    try:
        docs = db.collection('latest_videos').where('id', '==', video_id).get()
        for doc in docs:
            doc.reference.delete()
        return True
    except:
        return False

@app.route('/')
def index():
    latest_videos = load_videos()
    return render_template('index.html', latest_videos=latest_videos)

@app.route('/tutorials')
def tutorials():
    all_tutorials = load_tutorials()
    return render_template('tutorials.html', tutorials=all_tutorials)

@app.route('/admin-login', methods=['POST'])
def admin_login():
    email = request.form.get('email')
    password = request.form.get('password')
    
    if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
        session['is_admin'] = True
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Invalid credentials'})

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/verify-admin', methods=['POST'])
def verify_admin():
    admin_password = request.form.get('admin_password')
    if admin_password == ADMIN_PASSWORD:
        session['is_admin'] = True
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Invalid admin password'})

@app.route('/add-tutorial', methods=['POST'])
def add_tutorial():
    if not session.get('is_admin'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    # Check if it's a latest video (no description)
    if not request.form.get('description'):
        videos = load_videos()
        new_id = max([v.get('id', 0) for v in videos], default=-1) + 1
        
        video = {
            'id': new_id,
            'title': request.form.get('title'),
            'video_embed': request.form.get('video_embed')
        }
        
        save_video(video)
        return redirect(url_for('index'))
    
    # Handle full tutorial
    tutorials = load_tutorials()
    new_id = max([t.get('id', 0) for t in tutorials], default=-1) + 1
    
    # Handle multiple code snippets and file URLs
    code_snippets = []
    code_urls = []
    files_urls = []
    
    for key, value in request.form.items():
        if key.startswith('code_snippet_') and value.strip():
            code_snippets.append(value)
        elif key.startswith('code_url_') and value.strip():
            code_urls.append(value)
        elif key.startswith('files_url_') and value.strip():
            files_urls.append(value)
    
    tutorial = {
        'id': new_id,
        'title': request.form.get('title'),
        'description': request.form.get('description'),
        'code_snippets': code_snippets,
        'video_embed': request.form.get('video_embed'),
        'code_urls': code_urls,
        'files_urls': files_urls
    }
    
    save_tutorial(tutorial)
    return redirect(url_for('tutorials'))

@app.route('/delete-tutorial/<int:tutorial_id>', methods=['POST'])
def delete_tutorial(tutorial_id):
    if not session.get('is_admin'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    delete_tutorial_by_id(tutorial_id)
    return redirect(url_for('tutorials'))

@app.route('/delete-video/<int:video_id>', methods=['POST'])
def delete_video(video_id):
    if not session.get('is_admin'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    delete_video_by_id(video_id)
    return redirect(url_for('index'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)