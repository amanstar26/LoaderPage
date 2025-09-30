# app.py
import base64
import math
import os
from flask import Flask, request, jsonify, abort, Response, url_for

app = Flask(__name__)

# ---------------------
# Helpers
# ---------------------
def urlsafe_b64_encode_no_padding(s: str) -> str:
    """Encode to URL-safe base64 and strip padding '=' so it fits nicely in path."""
    b = s.encode("utf-8")
    enc = base64.urlsafe_b64encode(b).decode("utf-8")
    return enc.rstrip("=")

def urlsafe_b64_decode_padding(s: str) -> str:
    """Decode a urlsafe base64 string that may be missing padding."""
    # restore padding
    padding = '=' * (-len(s) % 4)
    data = s + padding
    return base64.urlsafe_b64decode(data.encode("utf-8")).decode("utf-8")

def split_into_chunks(s: str, min_chunks=3, max_chunks=6):
    """Split a string into random-ish chunks (deterministic split for server-side).
       This is used to create an array of pieces in the served HTML to slightly obfuscate the
       base64 string in the page source (we reverse them on the client to reassemble)."""
    # We use a simple deterministic chunking so the server doesn't use randomness.
    n = max(min_chunks, min(max_chunks, (len(s) // 12) + 1))
    n = min(n, len(s))
    chunk_len = math.ceil(len(s) / n)
    parts = [s[i:i+chunk_len] for i in range(0, len(s), chunk_len)]
    return parts

# ---------------------
# API: /encode
# ---------------------
@app.route("/encode", methods=["GET", "POST"])
def encode():
    """
    Accepts:
      - POST JSON: {"url":"https://example.com/target"}
      - GET query:  /encode?url=https://example.com/target
    Returns JSON: {"loader_url":"https://<host>/<b64>"}
    """
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        raw = data.get("url") or request.form.get("url")
    else:
        raw = request.args.get("url")

    if not raw:
        return jsonify({"error":"missing 'url' parameter"}), 400

    # basic validation
    if not (raw.startswith("http://") or raw.startswith("https://")):
        return jsonify({"error":"url must start with http:// or https://"}), 400

    # encode
    b64 = urlsafe_b64_encode_no_padding(raw)

    # construct loader url using the host used for the request
    # use request.url_root (ends with /)
    host = request.url_root.rstrip("/")
    loader_url = f"{host}/{b64}"
    return jsonify({"loader_url": loader_url, "b64": b64})

# ---------------------
# Loader page: /<b64>
# ---------------------
@app.route("/<path:b64path>", methods=["GET"])
def loader_page(b64path):
    """
    When the user visits /<base64>, serve the loader page which:
      1) reassembles the base64 (from an array of split parts reversed),
      2) decodes the original URL,
      3) shows a 5s loader with countdown,
      4) redirects to the decoded URL.
    """
    # validate input (only allow base64 urlsafe characters)
    if not all(c.isalnum() or c in "-_" for c in b64path):
        abort(404)

    try:
        # decode to ensure it's a valid b64 encoded URL. If not valid, abort.
        original = urlsafe_b64_decode_padding(b64path)
    except Exception:
        abort(404)

    # create small chunks to include in the page (server-side split -> client will reverse)
    parts = split_into_chunks(b64path, min_chunks=3, max_chunks=6)
    # reverse the parts in the HTML so the client must reverse to reassemble
    # (this only slightly hides the raw base64 in the HTML)
    parts_js_array = ",".join(f'"{p}"' for p in parts[::-1])

    # The HTML loader (single file)
    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Redirecting…</title>
<style>
  :root{{--bg1:#667eea;--bg2:#764ba2}}
  html,body{{height:100%;margin:0}}
  body{{display:flex;align-items:center;justify-content:center;font-family:Inter,Segoe UI,Roboto,system-ui,-apple-system;
         background:linear-gradient(135deg,var(--bg1),var(--bg2));color:#fff;flex-direction:column;text-align:center;padding:24px}}
  .card{{backdrop-filter: blur(6px);padding:28px;border-radius:18px;box-shadow:0 8px 30px rgba(0,0,0,0.25);max-width:520px;width:100%}}
  .ring{{width:110px;height:110px;border-radius:50%;position:relative;margin:0 auto 18px;display:grid;place-items:center}}
  .ring:before{{content:"";position:absolute;inset:0;border-radius:50%;
               background:conic-gradient(from 0deg,#fff 0 25%,rgba(255,255,255,0.12) 25% 100%);
               -webkit-mask:radial-gradient(farthest-side,transparent calc(100% - 14px),#000 0);
               animation:spin 1.2s linear infinite;transform-origin:center}}
  .dot{{width:20px;height:20px;border-radius:50%;background:linear-gradient(180deg,#fff,#f0f0f0);
       box-shadow:0 6px 20px rgba(0,0,0,0.25)}}
  @keyframes spin{{to{{transform:rotate(360deg)}}}}
  h1{{margin:0 0 6px;font-size:20px}} p{{margin:0;color:rgba(255,255,255,0.92)}}
  .count{{margin-top:10px;font-weight:600;letter-spacing:0.6px}} .meta{{margin-top:12px;font-size:13px;opacity:.85}}
  .btns{{display:flex;gap:10px;justify-content:center;margin-top:16px}} .btn{{border:0;padding:10px 14px;border-radius:10px;font-weight:600;cursor:pointer}}
  .skip{{background:transparent;color:#fff;border:1px solid rgba(255,255,255,0.18)}} .open{{background:#fff;color:#3b2d87}}
</style>
</head>
<body>
  <div class="card" role="main" aria-live="polite">
    <div class="ring" aria-hidden="true"><div class="dot"></div></div>
    <h1>Preparing your link…</h1>
    <p class="meta">You will be redirected shortly. If auto-redirect is blocked, use the Open button.</p>
    <div class="count">Redirecting in <span id="t">5</span>s</div>
    <div class="btns">
      <button id="skip" class="btn skip">Skip</button>
      <button id="open" class="btn open" style="display:none">Open Link</button>
    </div>
  </div>

<script>
(function(){
  // parts array (server-split, reversed in server so client needs to reverse to reassemble)
  const parts = [{parts_array}];

  // reassemble
  const joined = parts.slice().reverse().join('');
  // decode base64 safely (restore padding)
  function decodeBase64UrlSafe(b64){
    try{
      const pad = '='.repeat((4 - (b64.length % 4)) % 4);
      return atob(b64 + pad);
    }catch(e){
      return null;
    }
  }
  const target = decodeBase64UrlSafe(joined) || '/';

  // UI refs
  const elT = document.getElementById('t');
  const skip = document.getElementById('skip');
  const openBtn = document.getElementById('open');

  let seconds = 5;
  const iv = setInterval(()=>{
    elT.textContent = seconds;
    if(seconds <= 0){
      clearInterval(iv);
      try{ window.location.href = target; }catch(e){}
      openBtn.style.display = 'inline-block';
    }
    seconds--;
  }, 1000);

  skip.addEventListener('click', ()=>{ try{ window.location.href = target; }catch(e){} });
  openBtn.addEventListener('click', ()=>{ try{ window.open(target, '_blank'); }catch(e){} });

  // wipe arrays and local variables a little later
  setTimeout(()=>{ try{ for(let i=0;i<parts.length;i++) parts[i]=''; }catch(e){} }, 3000);
})();
</script>
</body>
</html>
""".replace("{parts_array}", parts_js_array)

    return Response(html, mimetype="text/html")

# ---------------------
# Run
# ---------------------
if __name__ == "__main__":
    # For quick local testing run: python app.py
    # In production, use a proper WSGI server (gunicorn/uvicorn) and set HOST/PORT via env vars
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
