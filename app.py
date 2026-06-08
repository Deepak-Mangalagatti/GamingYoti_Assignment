import sqlite3
import hashlib
import requests
import json
import os
from datetime import datetime
from flask import Flask, render_template_string, request, redirect, session, jsonify

app = Flask(__name__)
app.secret_key = "mysecretkey123"

# my api keys for yoti
BEARER_TOKEN = "Enter your BEARER_TOKEN"
SDK_KEY = "Enter your SDK_KEY"

# yoti urls
YOTI_API = "https://age.yoti.com/api/v1"

# this is what we send to yoti when creating a session
YOTI_SESSION_DATA = {
    "type": "OVER",
    "ttl": 900,
    "reference_id": "gamingyoti-test",
    "age_estimation": {
        "allowed": True,
        "threshold": 18,
        "level": "PASSIVE",
        "retry_limit": 1,
    },
    "digital_id": {
        "allowed": True,
        "threshold": 18,
        "age_estimation_allowed": True,
        "age_estimation_threshold": 21,
        "retry_limit": 1,
    },
    "doc_scan": {
        "allowed": True,
        "threshold": 18,
        "authenticity": "AUTO",
        "level": "PASSIVE",
        "retry_limit": 1,
    },
    "callback": {"auto": False, "url": "https://www.yoti.com"},
    "notification_url": "https://webhook.site/2b7a0b2f-0751-4711-968a-de3469b92c3c",
    "cancel_url": "https://www.yoti.com",
    "retry_enabled": True,
    "resume_enabled": True,
    "synchronous_checks": True,
}

DATABASE = "gamingyoti.db"


# css that is used on all pages
PAGE_CSS = """
  body {
    font-family: 'Segoe UI', sans-serif;
    background: linear-gradient(135deg, #f4f7fb, #e8eef9);
    min-height: 100vh;
    margin: 0;
    padding: 20px;
  }

  .card {
    background: white;
    max-width: 500px;
    margin: 40px auto;
    padding: 32px;
    border-radius: 18px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.08), 0 2px 8px rgba(0,0,0,0.05);
  }

  h1 {
    font-size: 2rem;
    margin-bottom: 8px;
    color: #1e293b;
  }

  .subtitle { color: #64748b; font-size: 0.95rem; margin-bottom: 20px; }

  .form-group { margin-bottom: 16px; }

  label { display: block; font-weight: 600; margin-bottom: 6px; color: #374151; }

  input[type=text], input[type=email], input[type=password] {
    width: 100%;
    padding: 12px 14px;
    border: 1px solid #d0d7e2;
    border-radius: 10px;
    font-size: 15px;
    box-sizing: border-box;
  }

  input:focus {
    outline: none;
    border-color: #3b82f6;
    box-shadow: 0 0 0 4px rgba(59,130,246,0.15);
  }

  .btn {
    display: block;
    width: 100%;
    padding: 12px;
    font-size: 1rem;
    font-weight: 600;
    border: none;
    border-radius: 10px;
    cursor: pointer;
    margin-top: 10px;
    box-sizing: border-box;
  }

  .btn-blue { background: #3b82f6; color: white; }
  .btn-blue:hover { background: #2563eb; }
  .btn-green { background: #22c55e; color: white; }
  .btn-green:hover { background: #16a34a; }
  .btn-gray { background: #e5e7eb; color: #374151; }
  .btn-gray:hover { background: #d1d5db; }
  .btn:disabled { opacity: 0.6; cursor: not-allowed; }

  .msg-error   { background: #fef2f2; color: #b91c1c; border: 1px solid #fca5a5; padding: 12px; border-radius: 8px; margin-bottom: 16px; }
  .msg-success { background: #f0fdf4; color: #166534; border: 1px solid #86efac; padding: 12px; border-radius: 8px; margin-bottom: 16px; }
  .msg-warn    { background: #fffbeb; color: #92400e; border: 1px solid #fcd34d; padding: 12px; border-radius: 8px; margin-bottom: 16px; }
  .msg-info    { background: #eff6ff; color: #1e40af; border: 1px solid #93c5fd; padding: 12px; border-radius: 8px; margin-bottom: 16px; }

  .hidden { display: none; }

  .spinner {
    display: inline-block;
    width: 14px;
    height: 14px;
    border: 2px solid #ccc;
    border-top-color: #fff;
    border-radius: 50%;
    animation: spin 0.7s linear infinite;
    vertical-align: middle;
    margin-right: 6px;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  hr { border: none; border-top: 1px solid #e5e7eb; margin: 20px 0; }

  .steps { margin: 12px 0; padding-left: 20px; }
  .steps li { margin-bottom: 8px; font-size: 0.95rem; color: #374151; }

  .info-table { width: 100%; border-collapse: collapse; margin-top: 10px; }
  .info-table td { padding: 10px 12px; border: 1px solid #e5e7eb; font-size: 0.93rem; }
  .info-table td:first-child { font-weight: 600; background: #f9fafb; width: 130px; color: #374151; }
"""


# register page html
REGISTER_PAGE = ("""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Register - GamingYoti</title>
  <style>""" + PAGE_CSS + """</style>
</head>
<body>
  <div class="card">
    <h1>GamingYoti</h1>
    <p class="subtitle">Create an account and verify your age with Yoti</p>
    <hr>

    {% if error %}
    <div class="msg-error" id="errorBox">{{ error }}</div>
    {% endif %}

    <form method="POST" action="/register" id="myForm">
      <div class="form-group">
        <label>Username</label>
        <input type="text" name="username" value="{{ username or '' }}" required minlength="3" placeholder="Enter username">
      </div>
      <div class="form-group">
        <label>Email</label>
        <input type="email" name="email" value="{{ email or '' }}" required placeholder="Enter email">
      </div>
      <div class="form-group">
        <label>Password (min 8 characters)</label>
        <input type="password" name="password" id="pwd" required minlength="8" placeholder="Enter password">
      </div>
      <div class="form-group">
        <label>Confirm Password</label>
        <input type="password" name="confirm_password" id="cpwd" required placeholder="Repeat password">
      </div>
      <button type="submit" class="btn btn-blue" id="submitBtn">Register and Start Verification</button>
    </form>
  </div>

  <script>
    document.getElementById('myForm').addEventListener('submit', function(e) {
      var pwd = document.getElementById('pwd').value;
      var cpwd = document.getElementById('cpwd').value;
      if (pwd != cpwd) {
        e.preventDefault();
        var box = document.getElementById('errorBox');
        if (!box) {
          box = document.createElement('div');
          box.id = 'errorBox';
          box.className = 'msg-error';
          this.parentNode.insertBefore(box, this);
        }
        box.textContent = 'Passwords do not match.';
        return;
      }
      var btn = document.getElementById('submitBtn');
      btn.disabled = true;
      btn.innerHTML = '<span class="spinner"></span> Please wait...';
    });
  </script>
</body>
</html>
""")


# verify page html - opens yoti tab automatically
VERIFY_PAGE = ("""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Verify Age - GamingYoti</title>
  <style>""" + PAGE_CSS + """</style>
</head>
<body>
  <div class="card">
    <h1>Age Verification</h1>
    <p class="subtitle">Hello <strong>{{ username }}</strong> ({{ email }})</p>
    <hr>

    <p>A Yoti verification tab has opened. Please follow these steps:</p>

    <ol class="steps">
      <li><strong>Step 1:</strong> Registration done and Yoti session created</li>
      <li><strong>Step 2:</strong> Complete the steps in the Yoti tab</li>
      <li><strong>Step 3:</strong> Come back here and click Get Results</li>
    </ol>

    <div id="statusMsg" class="hidden"></div>

    <button class="btn btn-green" id="getResultBtn" type="button">Get Results</button>

    <p style="margin-top:14px">
      <a href="/register" id="tryAgainLink" style="display:none; color:#3b82f6;">Go back and register again</a>
    </p>
  </div>

  <script>
    var yotiUrl = {{ verify_url | tojson }};
    var sessionId = {{ session_id | tojson }};

    var yotiTab = window.open(yotiUrl, '_blank');

    
    function showMessage(text, type) {
      var box = document.getElementById('statusMsg');
      box.textContent = text;
      box.className = 'msg-' + type;
    }

    document.getElementById('getResultBtn').addEventListener('click', function() {
      var btn = document.getElementById('getResultBtn');
      btn.disabled = true;
      btn.innerHTML = '<span class="spinner"></span> Please wait...';
      document.getElementById('statusMsg').className = 'hidden';

      fetch('/api/get-result', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId })
      })
      .then(function(resp) { return resp.json().then(function(data) { return { ok: resp.ok, data: data }; }); })
      .then(function(result) {
        if (!result.ok) {
          showMessage(result.data.error || 'Something went wrong.', 'error');
          document.getElementById('tryAgainLink').style.display = 'inline';
          btn.disabled = false;
          btn.innerHTML = 'Get Results';
          return;
        }
        if (result.data._verified) {
          window.location.href = '/success';
        } else {
          showMessage('Verification not complete yet. Finish the steps in the Yoti tab and try again.', 'warn');
          document.getElementById('tryAgainLink').style.display = 'inline';
          btn.disabled = false;
          btn.innerHTML = 'Get Results';
        }
      })
      .catch(function(err) {
        showMessage('Network error. Please try again.', 'error');
        btn.disabled = false;
        btn.innerHTML = 'Get Results';
      });
    });
  </script>
</body>
</html>
""")


# success page html - shown after verified
SUCCESS_PAGE = ("""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Verified - GamingYoti</title>
  <style>""" + PAGE_CSS + """</style>
</head>
<body>
  <div class="card">
    <h1>Age Verified</h1>
    <p class="subtitle">Welcome, <strong>{{ username }}</strong>! Your account has been created.</p>
    <hr>

    <div class="msg-success">
      Your age has been successfully confirmed by Yoti. You can now access GamingYoti.
    </div>

    <p><strong>Account Details:</strong></p>
    <table class="info-table">
      <tr><td>Username</td><td>{{ username }}</td></tr>
      <tr><td>Email</td><td>{{ email }}</td></tr>
      <tr><td>Status</td><td>Verified</td></tr>
      <tr><td>Verified On</td><td>{{ verified_at }}</td></tr>
      <tr>
        <td>Method</td>
        <td>
          {% if method == 'age_estimation' %}Age Estimation
          {% elif method == 'doc_scan' %}Document Scan
          {% elif method == 'digital_id' %}Digital ID
          {% else %}{{ method or 'Yoti AVS' }}{% endif %}
        </td>
      </tr>
      <tr>
        <td>Yoti Session</td>
        <td style="font-family: monospace; font-size: 0.8rem">{{ session_id[:16] }}...</td>
      </tr>
    </table>

    <br>
    <form action="/new-registration" method="get" style="margin: 0">
      <button type="submit" class="btn btn-blue">Register a New User</button>
    </form>
  </div>
</body>
</html>
""")


# this function sets up the database tables if they dont exist yet
def setup_database():
    db = sqlite3.connect(DATABASE)
    db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            username   TEXT NOT NULL UNIQUE,
            email      TEXT NOT NULL UNIQUE,
            password   TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS verifications (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER NOT NULL,
            session_id   TEXT NOT NULL,
            status       TEXT,
            method_used  TEXT,
            age_verified INTEGER,
            raw_result   TEXT,
            created_at   TEXT NOT NULL,
            completed_at TEXT
        )
    """)
    db.commit()
    db.close()


# returns a db connection
def get_db_connection():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db


# simple password hashing using sha256
def hash_password(password):
    salt = "somesalt123"
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    return hashed


# builds the headers needed for yoti api calls
def get_yoti_headers():
    headers = {
        "Authorization": "Bearer " + BEARER_TOKEN,
        "Yoti-SDK-Id": SDK_KEY,
        "Content-Type": "application/json"
    }
    return headers


# creates a new yoti session and returns the session id
def create_yoti_session():
    try:
        response = requests.post(
            YOTI_API + "/sessions",
            headers=get_yoti_headers(),
            json=YOTI_SESSION_DATA,
            timeout=30
        )
    except Exception as e:
        return None, "Could not connect to Yoti: " + str(e)

    if not response.ok:
        try:
            error_detail = response.json().get("message") or response.text
        except:
            error_detail = response.text

        if response.status_code == 401:
            return None, "Yoti rejected the SDK ID (401). Check your SDK_KEY in app.py. Details: " + str(error_detail)
        if response.status_code == 403:
            return None, "Yoti rejected the API key (403). Check your BEARER_TOKEN in app.py. Details: " + str(error_detail)
        return None, "Yoti error " + str(response.status_code) + ": " + str(error_detail)

    try:
        data = response.json()
    except:
        return None, "Yoti returned something we could not read."

    # yoti sometimes returns sessionId or id
    session_id = data.get("sessionId") or data.get("id")
    if not session_id:
        return None, "Yoti did not return a session ID."

    return session_id, None


# fetches the result of a yoti session
def fetch_yoti_result(session_id):
    try:
        response = requests.get(
            YOTI_API + "/sessions/" + session_id + "/result",
            headers={
                "Authorization": "Bearer " + BEARER_TOKEN,
                "Yoti-SDK-Id": SDK_KEY
            },
            timeout=30
        )
    except Exception as e:
        return None, "Network error: " + str(e)

    if not response.ok:
        try:
            error_detail = response.json().get("message") or response.text
        except:
            error_detail = response.text
        return None, "Yoti error " + str(response.status_code) + ": " + str(error_detail)

    try:
        data = response.json()
    except:
        return None, "Could not read Yoti response."

    return data, None


# checks if yoti said the person is verified
def check_if_verified(data):
    if not data:
        return False
    status = (data.get("status") or data.get("state") or "").upper()
    if status in ["COMPLETE", "COMPLETED", "SUCCESS", "PASSED", "PASS"]:
        return True
    if data.get("result") == True or data.get("passed") == True or data.get("verified") == True:
        return True
    if data.get("age") and isinstance(data["age"].get("verified"), bool):
        return data["age"]["verified"]
    return False


# saves the verified user to the database
def save_user_to_db(username, email, password, session_id, method, status, raw_data):
    db = get_db_connection()
    now = datetime.utcnow().isoformat()

    try:
        cursor = db.execute(
            "INSERT INTO users (username, email, password, created_at) VALUES (?, ?, ?, ?)",
            (username, email, hash_password(password), now)
        )
        user_id = cursor.lastrowid
    except sqlite3.IntegrityError as e:
        db.close()
        if "username" in str(e):
            return None, "Username already taken."
        return None, "Email already registered."

    db.execute(
        "INSERT INTO verifications (user_id, session_id, status, method_used, age_verified, raw_result, created_at, completed_at) VALUES (?, ?, ?, ?, 1, ?, ?, ?)",
        (user_id, session_id, status, method, json.dumps(raw_data), now, now)
    )
    db.commit()
    db.close()
    return user_id, None


# checks if username or email already exists in db
def check_user_exists(username, email):
    db = get_db_connection()
    user = db.execute(
        "SELECT id FROM users WHERE username = ? OR email = ?",
        (username, email)
    ).fetchone()
    if user:
        by_username = db.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        db.close()
        if by_username:
            return "Username already taken."
        return "Email already registered."
    db.close()
    return None



# routes / pages


@app.route("/")
def home():
    return redirect("/register")


@app.route("/new-registration")
def new_registration():
    # clear session so fresh user can register
    session.clear()
    return redirect("/register")


@app.route("/register", methods=["GET", "POST"])
def register_page():
    # just show the form
    if request.method == "GET":
        return render_template_string(REGISTER_PAGE)

    # get form values
    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    confirm = request.form.get("confirm_password", "")

    # basic checks
    if not username or not email or not password:
        return render_template_string(REGISTER_PAGE, error="All fields are required.", username=username, email=email)

    if len(username) < 3:
        return render_template_string(REGISTER_PAGE, error="Username must be at least 3 characters.", username=username, email=email)

    if "@" not in email:
        return render_template_string(REGISTER_PAGE, error="Please enter a valid email address.", username=username, email=email)

    if len(password) < 8:
        return render_template_string(REGISTER_PAGE, error="Password must be at least 8 characters.", username=username, email=email)

    if password != confirm:
        return render_template_string(REGISTER_PAGE, error="Passwords do not match.", username=username, email=email)

    # check if user already exists
    conflict = check_user_exists(username, email)
    if conflict:
        return render_template_string(REGISTER_PAGE, error=conflict, username=username, email=email)

    # create yoti session
    yoti_session_id, error = create_yoti_session()
    if error:
        return render_template_string(REGISTER_PAGE, error=error, username=username, email=email)

    # save to flask session temporarily until verified
    session.clear()
    session["username"] = username
    session["email"] = email
    session["password"] = password
    session["yoti_session_id"] = yoti_session_id

    return redirect("/verify")


@app.route("/verify")
def verify_page():
    yoti_session_id = session.get("yoti_session_id")
    if not yoti_session_id:
        return redirect("/register")

    # build the yoti url the user will visit
    yoti_url = "https://age.yoti.com/age-estimation?sessionId=" + yoti_session_id + "&sdkId=" + SDK_KEY

    return render_template_string(
        VERIFY_PAGE,
        username=session.get("username", "User"),
        email=session.get("email", ""),
        verify_url=yoti_url,
        session_id=yoti_session_id
    )


@app.route("/api/get-result", methods=["POST"])
def get_result():
    yoti_session_id = session.get("yoti_session_id")
    if not yoti_session_id:
        return jsonify({"error": "No session found. Please register again."}), 400

    body = request.get_json() or {}
    sid = body.get("session_id") or yoti_session_id

    # ask yoti if the person passed
    data, error = fetch_yoti_result(sid)
    if error:
        return jsonify({"error": error}), 502

    verified = check_if_verified(data)
    method = data.get("method")
    status = (data.get("status") or data.get("state") or "UNKNOWN").upper()
    data["_verified"] = verified
    data["_method_used"] = method

    if not verified:
        return jsonify(data)

    # verified - save to database
    username = session.get("username")
    email = session.get("email")
    password = session.get("password")

    if not username or not email or not password:
        return jsonify({"error": "Session data missing. Please register again."}), 400

    user_id, error = save_user_to_db(username, email, password, sid, method, status, data)
    if error:
        return jsonify({"error": error}), 409

    # move data to verified session
    session.pop("password", None)
    session.pop("yoti_session_id", None)
    session["verified"] = True
    session["verified_method"] = method
    session["verified_at"] = datetime.utcnow().isoformat()
    session["verified_session_id"] = sid

    return jsonify(data)


@app.route("/success")
def success_page():
    if not session.get("verified"):
        return redirect("/register")

    # format the date nicely
    raw_date = session.get("verified_at", "")
    try:
        nice_date = datetime.fromisoformat(raw_date).strftime("%d %b %Y, %H:%M")
    except:
        nice_date = raw_date or "Unknown"

    return render_template_string(
        SUCCESS_PAGE,
        username=session.get("username", ""),
        email=session.get("email", ""),
        method=session.get("verified_method", ""),
        verified_at=nice_date,
        session_id=session.get("verified_session_id", "")
    )


# old urls just redirect to register
@app.route("/login")
@app.route("/signup")
def old_pages():
    return redirect("/register")


# start the app
if __name__ == "__main__":
    setup_database()
    print("Starting GamingYoti...")
    print("Go to: http://localhost:5000")
    app.run(debug=True, port=5000)
