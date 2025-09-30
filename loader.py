import base64
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Use /{base64} path to redirect."}

@app.get("/{b64}", response_class=HTMLResponse)
def loader(b64: str):
    try:
        pad = "=" * (-len(b64) % 4)
        target = base64.urlsafe_b64decode(b64 + pad).decode()
    except Exception:
        return HTMLResponse("Invalid Base64 string", status_code=400)

    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Redirecting…</title>
<style>
body{{display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0;font-family:sans-serif;background:#222;color:#fff;text-align:center}}
.spinner{{width:60px;height:60px;border:6px solid rgba(255,255,255,.3);border-top-color:#fff;border-radius:50%;animation:spin 1s linear infinite;margin:0 auto 20px}}
@keyframes spin{{to{{transform:rotate(360deg)}}}}
</style>
</head>
<body>
<div>
<div class="spinner"></div>
<h2>Redirecting in <span id="t">5</span>s…</h2>
<p>If it doesn’t work, <a href="{target}">click here</a>.</p>
</div>
<script>
let t=5;
const iv=setInterval(()=>{{t--;document.getElementById("t").textContent=t;if(t<=0){{clearInterval(iv);window.location.href="{target}";}}}},1000);
</script>
</body>
</html>
"""
    return HTMLResponse(content=html)

# Local development server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
