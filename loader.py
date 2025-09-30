import base64
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

# Fake 404 page for invalid access
def fake_404_page():
    html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>404 Not Found</title>
<style>
body {
    margin: 0;
    height: 100vh;
    display: flex;
    justify-content: center;
    align-items: center;
    font-family: 'Segoe UI', sans-serif;
    background: #111;
    color: #fff;
    text-align: center;
}
h1 { font-size: 48px; margin-bottom: 20px; }
p { font-size: 18px; }
</style>
</head>
<body>
<div>
<h1>404</h1>
<p>Page not found</p>
</div>
</body>
</html>"""
    return HTMLResponse(content=html, status_code=404)

@app.get("/{b64}", response_class=HTMLResponse)
async def loader(b64: str):
    # Security: Only allow URL-safe Base64 strings
    try:
        pad = "=" * (-len(b64) % 4)
        target = base64.urlsafe_b64decode(b64 + pad).decode("utf-8")
    except Exception:
        # Invalid Base64 → show fake 404
        return fake_404_page()

    # Optional: extra security check (e.g., only allow links to certain domains)
    # if not target.startswith("https://adrinolinks.com/"):
    #     return fake_404_page()

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Redirecting...</title>
<style>
body {{
  margin: 0;
  height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  font-family: 'Segoe UI', sans-serif;
  background: linear-gradient(135deg, #6a11cb 0%, #2575fc 100%);
  color: #fff;
  overflow: hidden;
}}
.loader-container {{
  text-align: center;
}}
.spinner {{
  width: 80px;
  height: 80px;
  border: 8px solid rgba(255, 255, 255, 0.2);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 20px;
}}
@keyframes spin {{ to {{ transform: rotate(360deg); }} }}
h1 {{ font-size: 24px; margin-bottom: 10px; }}
p {{ font-size: 16px; }}
.countdown {{ font-weight: bold; }}
a {{ color: #fff; text-decoration: underline; }}
</style>
</head>
<body>
<div class="loader-container">
  <div class="spinner"></div>
  <h1>Redirecting in <span class="countdown" id="t">5</span>s...</h1>
  <p>If it doesn’t redirect automatically, <a href="{target}">click here</a></p>
</div>
<script>
let t = 5;
const iv = setInterval(() => {{
    t--;
    document.getElementById('t').textContent = t;
    if (t <= 0) {{
        clearInterval(iv);
        window.location.href = "{target}";
    }}
}}, 1000);
</script>
</body>
</html>"""

    return HTMLResponse(content=html)

# Local development server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
