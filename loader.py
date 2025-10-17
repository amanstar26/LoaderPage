import secrets
import sqlite3
import requests
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

app = FastAPI()

# ---------------- CONFIG ----------------
DB_PATH = "tokens.db"
RECAPTCHA_SITE_KEY = "6LdRye0rAAAAAJdv5WzcynyTqL1MMGxtQ1MPHcWw"
RECAPTCHA_SECRET_KEY = "6LdRye0rAAAAAFbkHSf-lNCeK3Ap_zDTxlXOr_A1"

# ---------------- DATABASE ----------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT UNIQUE NOT NULL,
            target_url TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def save_token(token: str, url: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO tokens (token, target_url) VALUES (?, ?)", (token, url))
    conn.commit()
    conn.close()

def get_url_from_token(token: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT target_url FROM tokens WHERE token = ?", (token,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None

def delete_token(token: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM tokens WHERE token = ?", (token,))
    conn.commit()
    conn.close()

# Initialize database on startup
init_db()

# ---------------- HTML HELPERS ----------------
def fake_404_page():
    return HTMLResponse("""
    <html><body style="text-align:center;font-family:sans-serif;color:#fff;background:#111;">
    <h1>404</h1><p>Page not found</p></body></html>""", status_code=404)

@app.exception_handler(StarletteHTTPException)
async def custom_404_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return fake_404_page()
    return HTMLResponse(content=str(exc.detail), status_code=exc.status_code)

# ---------------- API ----------------
@app.get("/generate")
async def generate_link(url: str):
    token = secrets.token_urlsafe(32)
    save_token(token, url)
    protected_link = f"https://demon-lord.vercel.app/redirect/{token}"
    return {"protected": protected_link}

@app.get("/redirect/{token}", response_class=HTMLResponse)
async def captcha_page(token: str):
    target = get_url_from_token(token)
    if not target:
        return fake_404_page()

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Verify you're not a robot</title>
<script src="https://www.google.com/recaptcha/api.js" async defer></script>
<style>
body {{
  margin: 0; height: 100vh; display: flex; justify-content: center; align-items: center;
  background: linear-gradient(135deg,#6a11cb,#2575fc); color: #fff; font-family: 'Segoe UI',sans-serif;
}}
.container {{ background: rgba(0,0,0,0.4); padding: 40px; border-radius: 16px; text-align: center; }}
.h1 {{ font-size: 24px; margin-bottom: 20px; }}
button {{ margin-top:20px; background:#fff; color:#2575fc; border:none; padding:10px 20px;
  font-size:16px; border-radius:8px; cursor:pointer; }}
.small {{ margin-top:10px; font-size:14px; color:#ccc; }}
</style>
</head>
<body>
  <div class="container">
    <div class="h1">Verify you're not a robot</div>
    <form method="POST" action="/verify">
      <input type="hidden" name="token" value="{token}">
      <div class="g-recaptcha" data-sitekey="{RECAPTCHA_SITE_KEY}"></div>
      <button type="submit">Verify</button>
      <div class="small">Protected by reCAPTCHA</div>
    </form>
  </div>
</body>
</html>"""
    return HTMLResponse(content=html)

@app.post("/verify")
async def verify(token: str = Form(...), g_recaptcha_response: str = Form(...)):
    verify_url = "https://www.google.com/recaptcha/api/siteverify"
    data = {"secret": RECAPTCHA_SECRET_KEY, "response": g_recaptcha_response}
    res = requests.post(verify_url, data=data).json()

    if not res.get("success"):
        return HTMLResponse("<h2>❌ Verification failed</h2><p>Try again.</p>", status_code=400)

    target = get_url_from_token(token)
    if not target:
        return fake_404_page()

    # (Optional) delete token after use
    # delete_token(token)

    return RedirectResponse(url=target)

# ---------------- Run Locally ----------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
