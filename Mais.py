import os
import sys
import socket
import random
import qrcode
import base64

from io import BytesIO

VENV = "venv"

# =========================
# AUTO VENV
# =========================
if not os.path.exists(VENV):
    print("📦 Criando venv...")
    os.system("python3 -m venv venv")

if sys.prefix == sys.base_prefix:
    print("📦 Instalando dependências...")
    os.system(f"{VENV}/bin/pip install --upgrade pip")
    os.system(f"{VENV}/bin/pip install flask flask-socketio pynput qrcode pillow")
    print("🚀 Reiniciando no venv...\n")

    os.execv(
        f"{VENV}/bin/python",
        [f"{VENV}/bin/python"] + sys.argv
    )

# =========================
# IMPORTS
# =========================
from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, emit
from pynput.mouse import Controller, Button

# =========================
# APP
# =========================
app = Flask(__name__)

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="threading"
)

mouse = Controller()

clients = set()

PASSWORD = str(random.randint(1000, 9999))

SENS = 2.6

# =========================
# IP
# =========================
def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except:
        ip = "127.0.0.1"

    s.close()

    return ip

# =========================
# QR CODE
# =========================
def make_qr(data):
    img = qrcode.make(data)

    buf = BytesIO()

    img.save(buf, format="PNG")

    return base64.b64encode(buf.getvalue()).decode()

# =========================
# HTML
# =========================
@app.route("/")
def home():

    ip = get_ip()

    url = f"http://{ip}:5000"

    qr = make_qr(url)

    return render_template_string(f"""
<!DOCTYPE html>
<html lang="pt-br">

<head>

<meta charset="UTF-8">

<meta name="viewport"
content="width=device-width,
initial-scale=1.0,
maximum-scale=1.0,
user-scalable=no">

<title>BLACK REMOTE</title>

<script src="https://cdn.socket.io/4.7.2/socket.io.min.js"></script>

<style>

* {{
    margin:0;
    padding:0;
    box-sizing:border-box;
}}

body {{
    background:#000;
    overflow:hidden;
    height:100vh;
    font-family:Arial;
    touch-action:none;
}}

#pad {{
    position:absolute;
    inset:0;
    background:#000;
}}

.top {{
    position:absolute;
    top:0;
    left:0;
    right:0;

    background:rgba(0,0,0,.93);

    color:#00ff9d;

    text-align:center;

    padding:12px;

    z-index:999;

    border-bottom:1px solid #00ff9d;
}}

.top img {{
    margin-top:8px;
    border-radius:10px;
}}

.btn {{
    position:absolute;

    bottom:30px;
    left:50%;

    transform:translateX(-50%);

    border:none;

    background:#00ff9d;

    color:#000;

    font-weight:bold;

    padding:18px 50px;

    border-radius:50px;

    font-size:18px;

    box-shadow:0 0 30px #00ff9d;

    z-index:999;
}}

.btn:active {{
    transform:translateX(-50%) scale(.93);
}}

.status {{
    position:absolute;

    top:120px;
    left:50%;

    transform:translateX(-50%);

    background:rgba(0,255,100,.15);

    color:#00ff9d;

    padding:8px 20px;

    border-radius:40px;

    display:none;

    z-index:999;
}}

</style>

</head>

<body>

<div class="top">

🔥 BLACK REMOTE 🔥

<br>

Senha:
<b>{PASSWORD}</b>

<br>

<img src="data:image/png;base64,{qr}" width="100">

</div>

<div id="status" class="status">

✅ CONECTADO

</div>

<div id="pad"></div>

<button class="btn" onclick="connect()">
CONECTAR
</button>

<script>

let socket;

let connected = false;

let lx = 0;
let ly = 0;

let lastMove = 0;

let pressTimer;

function vibrate(ms=20){{
    if(navigator.vibrate){{
        navigator.vibrate(ms);
    }}
}}

function connect(){{

    const pass = prompt("Senha:");

    if(!pass) return;

    socket = io();

    socket.emit("auth", {{
        password:pass
    }});

    socket.on("ok", ()=>{{

        connected = true;

        document.getElementById("status")
        .style.display = "block";

        vibrate(100);

        document.documentElement
        .requestFullscreen?.();

        alert("🔥 Conectado!");

    }});

    socket.on("fail", ()=>{{
        alert("❌ Senha errada");
    }});

}}

const pad = document.getElementById("pad");

pad.addEventListener("touchstart", e=>{{

    if(!connected) return;

    const t = e.touches[0];

    lx = t.clientX;
    ly = t.clientY;

    pressTimer = setTimeout(()=>{{
        socket.emit("right_click");
        vibrate(50);
    }},700);

}});

pad.addEventListener("touchmove", e=>{{

    if(!connected) return;

    e.preventDefault();

    clearTimeout(pressTimer);

    const now = Date.now();

    if(now - lastMove < 8) return;

    lastMove = now;

    const t = e.touches[0];

    const dx = (t.clientX - lx) * {SENS};

    const dy = (t.clientY - ly) * {SENS};

    lx = t.clientX;
    ly = t.clientY;

    socket.emit("move",{{
        x:dx,
        y:dy
    }});

}});

pad.addEventListener("touchend", ()=>{{

    clearTimeout(pressTimer);

    if(!connected) return;

    socket.emit("click");

    vibrate(30);

}});

// Scroll 2 dedos
pad.addEventListener("touchmove", e=>{{

    if(!connected) return;

    if(e.touches.length == 2){{

        e.preventDefault();

        const dy = e.touches[0].clientY - ly;

        socket.emit("scroll",{{
            y:dy
        }});

        ly = e.touches[0].clientY;

    }}

}});

</script>

</body>
</html>
""")

# =========================
# AUTH
# =========================
@socketio.on("auth")
def auth(data):

    if data.get("password") == PASSWORD:

        clients.add(request.sid)

        emit("ok")

        print("💚 Cliente conectado")

    else:
        emit("fail")

# =========================
# MOVE
# =========================
@socketio.on("move")
def move(data):

    if request.sid not in clients:
        return

    mouse.move(
        float(data.get("x", 0)),
        float(data.get("y", 0))
    )

# =========================
# LEFT CLICK
# =========================
@socketio.on("click")
def click():

    if request.sid in clients:
        mouse.click(Button.left, 1)

# =========================
# RIGHT CLICK
# =========================
@socketio.on("right_click")
def right_click():

    if request.sid in clients:
        mouse.click(Button.right, 1)

# =========================
# SCROLL
# =========================
@socketio.on("scroll")
def scroll(data):

    if request.sid in clients:

        mouse.scroll(
            0,
            int(data.get("y", 0))
        )

# =========================
# START
# =========================
if __name__ == "__main__":

    print("\\n🔥 BLACK REMOTE")
    print(f"🔐 Senha: {PASSWORD}")
    print(f"🌐 IP: {get_ip()}:5000\\n")

    socketio.run(
        app,
        host="0.0.0.0",
        port=5000,
        allow_unsafe_werkzeug=True
)
