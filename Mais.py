import os
import sys
import socket
import random
import qrcode
from io import BytesIO
import base64

VENV = "venv"

if not os.path.exists(VENV):
    print("📦 Criando venv...")
    os.system("python3 -m venv venv")

if sys.prefix == sys.base_prefix:
    print("📦 Instalando dependências...")
    os.system(f"{VENV}/bin/pip install --upgrade pip")
    os.system(f"{VENV}/bin/pip install flask flask-socketio pynput qrcode pillow")
    print("🚀 Reiniciando no venv...\n")
    os.execv(f"{VENV}/bin/python", [f"{VENV}/bin/python"] + sys.argv)

from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, emit
from pynput.mouse import Controller, Button

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

mouse = Controller()
clients = set()

PASSWORD = str(random.randint(1000, 9999))
SENS = 2.6

def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip

def make_qr(data):
    img = qrcode.make(data)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()

@app.route("/")
def home():
    ip = get_ip()
    url = f"http://{ip}:5000"
    qr = make_qr(url)

    return render_template_string(f"""
    <!DOCTYPE html>
    <html lang="pt">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>REMOTE</title>
        <script src="https://cdn.socket.io/4.7.2/socket.io.min.js"></script>
        <style>
            * {{ margin:0; padding:0; box-sizing:border-box; }}
            body {{
                background: #000000;
                color: #00ff9d;
                font-family: 'Courier New', monospace;
                overflow: hidden;
                height: 100vh;
                touch-action: none;
            }}
            .top-bar {{
                position: absolute;
                top: 0; left: 0; right: 0;
                background: rgba(0,0,0,0.92);
                padding: 12px 10px;
                text-align: center;
                z-index: 10;
                border-bottom: 1px solid #00ff9d;
                font-size: 13px;
            }}
            #pad {{
                position: absolute;
                top: 68px;
                left: 0; right: 0; bottom: 0;
                background: #000000;
                border-top: 1px dashed rgba(0, 255, 157, 0.3);
            }}
            .connect-btn {{
                position: absolute;
                bottom: 35px;
                left: 50%;
                transform: translateX(-50%);
                background: #00ff9d;
                color: #000;
                border: none;
                padding: 16px 50px;
                border-radius: 50px;
                font-size: 17px;
                font-weight: bold;
                box-shadow: 0 0 30px #00ff9d;
                z-index: 30;
                transition: all 0.2s;
            }}
            .connect-btn:active {{
                transform: translateX(-50%) scale(0.92);
            }}
            .status {{
                position: absolute;
                top: 75px;
                left: 50%;
                transform: translateX(-50%);
                background: rgba(0,255,100,0.15);
                color: #00ff9d;
                padding: 6px 20px;
                border-radius: 30px;
                font-size: 14px;
                display: none;
                z-index: 20;
            }}
        </style>
    </head>
    <body>
        <div class="top-bar">
            🐱‍💻 MOUSE REMOTE | Senha: <b>{PASSWORD}</b>
            <br>
            <img src="data:image/png;base64,{qr}" width="95" style="margin-top:8px;">
        </div>

        <div id="status" class="status">✅ CONECTADO - DESLIZE NA TELA</div>

        <div id="pad"></div>

        <button class="connect-btn" onclick="connect()">CONECTAR</button>

        <script>
            let socket;
            let connected = false;
            let lx = 0, ly = 0;
            let lastMove = 0;

            function connect() {{
                const pass = prompt("🔑 Digite a senha:", "");
                if (!pass) return;

                socket = io();
                socket.emit("auth", {{ password: pass }});

                socket.on("ok", () => {{
                    connected = true;
                    document.getElementById("status").style.display = "block";
                    alert("🔥 Conectado! Agora desliza o dedo na tela preta, amor...");
                }));

                socket.on("fail", () => alert("❌ Senha errada!"));
            }}

            const pad = document.getElementById("pad");

            // Touch Move - Mais suave
            pad.addEventListener("touchstart", e => {{
                if (!connected) return;
                const t = e.touches[0];
                lx = t.clientX;
                ly = t.clientY;
            }});

            pad.addEventListener("touchmove", e => {{
                if (!connected) return;
                e.preventDefault();

                const now = Date.now();
                if (now - lastMove < 16) return; // Limitando taxa de movimento
                lastMove = now;

                const t = e.touches[0];
                const dx = (t.clientX - lx) * {SENS};
                const dy = (t.clientY - ly) * {SENS};

                lx = t.clientX;
                ly = t.clientY;

                socket.emit("move", {{ x: dx, y: dy }});
            }});

            // Toque longo = Clique Esquerdo
            let longPressTimer;
            pad.addEventListener("touchstart", () => {{
                if (!connected) return;
                longPressTimer = setTimeout(() => {{
                    socket.emit("click");
                }}, 480);
            }});

            pad.addEventListener("touchend", () => {{
                clearTimeout(longPressTimer);
            }});
        </script>
    </body>
    </html>
    """)

@socketio.on("auth")
def auth(data):
    if data.get("password") == PASSWORD:
        clients.add(request.sid)
        emit("ok")
        print("💚 Cliente conectado")
    else:
        emit("fail")

@socketio.on("move")
def move(data):
    if request.sid not in clients: return
    mouse.move(float(data.get("x", 0)), float(data.get("y", 0)))

@socketio.on("click")
def click():
    if request.sid in clients:
        mouse.click(Button.left, 1)

if __name__ == "__main__":
    print("🚀 Tela Preta Minimalista Melhorada")
    print(f"🔐 Senha: {PASSWORD}")
    socketio.run(app, host="0.0.0.0", port=5000, allow_unsafe_werkzeug=True)
