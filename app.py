from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from flask_cors import CORS
import requests
import logging
import sqlite3
import os
import hashlib
import secrets
from dotenv import load_dotenv

load_dotenv() 

app = Flask(__name__, static_folder="static")
app.secret_key = 'your_secret_key_here'
CORS(app)

# ✅ 從環境變數讀取 API 金鑰
CHATGPT_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
print("🔑 GEMINI_API_KEY loaded (head):", GEMINI_API_KEY[:4])

print("🔑 ChatGPT Key from env:", CHATGPT_API_KEY)
print("🔑 Gemini Key from env:", GEMINI_API_KEY) 

logging.basicConfig(level=logging.INFO)

# ---------- Database ----------
DB_FILE = 'users.db'

def init_db():
    if not os.path.exists(DB_FILE):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                reset_token TEXT
            )
        ''')
        conn.commit()
        conn.close()

init_db()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ---------- Routes ----------

@app.route('/')
def index():
    return render_template('api_test.html')

@app.route('/api_test')
def api_test():
    return render_template("api_test.html")

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = hash_password(request.form['password'])

        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                      (username, email, password))
            conn.commit()
            flash('Registration successful. Please login.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Email already registered!', 'danger')
        finally:
            conn.close()

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['username']
        password = hash_password(request.form['password'])

        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password))
        user = c.fetchone()
        conn.close()

        if user:
            session['user'] = user[1]
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials', 'danger')

    return render_template('login.html')

@app.route('/forgot', methods=['GET', 'POST'])
def forgot():
    if request.method == 'POST':
        email = request.form['email']
        token = secrets.token_urlsafe(16)
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("UPDATE users SET reset_token=? WHERE email=?", (token, email))
        conn.commit()
        conn.close()
        flash(f"Reset link: http://localhost:5000/reset/{token} (for demo only)", 'info')
        return redirect(url_for('login'))
    return render_template('forgot.html')

@app.route('/reset/<token>', methods=['GET', 'POST'])
def reset(token):
    if request.method == 'POST':
        new_pw = request.form['new_password']
        confirm_pw = request.form['confirm_password']
        if new_pw == confirm_pw:
            hashed_pw = hash_password(new_pw)
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("UPDATE users SET password=?, reset_token=NULL WHERE reset_token=?", (hashed_pw, token))
            conn.commit()
            conn.close()
            flash('Password reset successfully.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Passwords do not match.', 'danger')
    return render_template('reset.html')

# ---------- APIs ----------

@app.route('/proxy_request', methods=['POST'])
def proxy_request():
    try:
        data = request.json
        api_url = data.get('api_url')
        method = data.get('method', 'GET').upper()
        headers = data.get('headers', {})
        body = data.get('body', None)

        logging.info(f"Proxy Request: {method} {api_url}")

        if not api_url:
            return jsonify({"error": "Please provide API URL"}), 400

        if method == 'GET':
            response = requests.get(api_url, headers=headers)
        elif method == 'POST':
            response = requests.post(api_url, json=body, headers=headers)
        else:
            return jsonify({"error": "Only GET and POST supported"}), 400

        return jsonify(response.json())

    except Exception as e:
        logging.error(f"Proxy error: {str(e)}")
        return jsonify({"error": str(e)}), 500

import openai  

@app.route('/chatgpt', methods=['POST'])
def chatgpt():
    try:
        data = request.json
        prompt = data.get("prompt", "").strip()
        feature = data.get("feature", "").strip()

        if not prompt:
            return jsonify({"error": "Please provide a prompt"}), 400

        
        if feature == "image":
            
            response = openai.Image.create(
                prompt=prompt,
                n=1,
                size="512x512"
            )
            image_url = response['data'][0]['url']
            return jsonify({
                "image_url": image_url,
                "original": prompt
            })

        
        feature_prompts = {
            "grammar": "Please correct the grammar in the following text:",
            "style": "Rewrite the following sentence in three different writing styles:",
            "inspiration": "Generate creative writing inspiration based on this idea:",
            "suggestion": "Give detailed writing suggestions and explain the issues:"
        }

        full_prompt = feature_prompts.get(feature, "Help with the following:") + "\n\n" + prompt

        chat_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful English writing assistant."},
                {"role": "user", "content": full_prompt}
            ]
        )

        reply = chat_response.choices[0].message.content.strip()

        return jsonify({
    "original": prompt,
    "response": reply
})


    except Exception as e:
        logging.error(f"ChatGPT API error: {str(e)}")
        return jsonify({"error": str(e)}), 500




@app.route('/status')
def status():
    return jsonify({"message": "API server is running!"})

# ---------- Run ----------

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)



