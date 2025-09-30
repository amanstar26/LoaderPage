import base64
import os
import json
import secrets
from urllib.parse import urlencode

# Temporary in-memory store (⚠️ will reset on every cold start in Vercel!)
URL_STORE = {}

def handler(request, response):
    method = request.method
    path = request.path.strip("/").split("/")
    
    # -------------------------------
    # 1. Encode API (POST/GET)
    # -------------------------------
    if len(path) == 1 and path[0] == "encode":
        if method == "POST":
            try:
                data = json.loads(request.body.decode())
                raw_url = data.get("url")
            except Exception:
                return response.status(400).json({"error": "invalid JSON"})
        else:
            raw_url = request.query.get("url")

        if not raw_url or not (raw_url.startswith("http://") or raw_url.startswith("https://")):
            return response.status(400).json({"error": "missing or invalid url"})

        token = secrets.token_urlsafe(12)
        URL_STORE[token] = raw_url

        host = os.environ.get("HOST", "https://your-project.vercel.app")
        loader_url = f"{host}/{token}"
        return response.json({"loader_url": loader_url, "token": token})

    # -------------------------------
    # 2. Loader page (/<token>)
    # -------------------------------
    elif len(path) == 1 and path[0]:
        token = path[0]
        target = URL_STORE.get(token)

        if not target:
            return response.status(404).send("Invalid or expired link.")

        # minimal loader page
        html = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>Redirecting…</title>
  <style>
    body {{
      font-family: sans-serif; display:flex; align-items:center;
      justify-content:center; height:100vh; flex-direction:column;
      background: linear-gradient(135deg,#667eea,#764ba2); color:#fff;
    }}
    .spinner {{
      border: 6px solid rgba(255,255,255,0.3);
      border-top: 6px solid #fff; border-radius: 50%;
      width: 60px; height: 60px; animation: spin 1s linear infinite;
      margin-bottom: 16px;
    }}
    @keyframes spin {{ 100% {{ transform: rotate(360deg); }} }}
  </style>
</head>
<body>
  <div class="spinner"></div>
  <h2>Redirecting in <span id="t">5</span>s…</h2>
  <script>
    let t = 5;
    const target = {json.dumps(target)};
    const el = document.getElementById("t");
    const iv = setInterval(()=>{
      el.textContent = t;
      if(t <= 0){ clearInterval(iv); window.location.href = target; }
      t--;
    },1000);
  </script>
</body>
</html>
"""
        return response.type("html").send(html)

    # -------------------------------
    # 3. Fallback
    # -------------------------------
    return response.status(404).json({"error": "Not found"})
