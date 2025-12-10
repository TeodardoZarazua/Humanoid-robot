import cv2
import socket
import time
import threading
from tkinter import *
from PIL import Image, ImageTk
import mediapipe as mp
import os

# ================================================================
# CONFIG SERVIDOR ESP32
# ================================================================
ESP32_IP = "192.168.10.175"
PORT = 12345

# ================================================================
# VARIABLES GLOBALES
# ================================================================
latest_frame = None
running = True

# GESTOS INDEPENDIENTES
latest_left_code = "1"
latest_left_name = "Quieto"
latest_right_code = "1"
latest_right_name = "Quieto"

client = None
connected = False
manual_mode = False

frame_lock = threading.Lock()
gesture_lock = threading.Lock()

mp_pose = mp.solutions.pose

# ================================================================
# COLORES ESTILO EVANGELION
# ================================================================
bg_color        = "#05040a"
panel_color     = "#141020"
neon_blue       = "#7ae0ff"
neon_purple     = "#8f3cff"
neon_green      = "#7CFF4F"
neon_orange     = "#ff9e00"
neon_red        = "#ff0055"
text_color      = "#f0f0f0"
button_bg       = "#1b1828"
button_border   = neon_purple

# ================================================================
# TKINTER UI
# ================================================================
root = Tk()
root.title("EVA-01 REMOTE LINK")
root.configure(bg=bg_color)

main_frame = Frame(root, bg=bg_color)
main_frame.pack(padx=20, pady=20)

# ------------------ CAMARA ------------------
camera_border = Frame(main_frame, bg=neon_purple, bd=4, relief="solid")
camera_border.grid(row=0, column=0, padx=20)

camera_label = Label(camera_border, bg="black")
camera_label.pack()

# ------------------ PANEL CONTROL ------------------
control_frame = Frame(
    main_frame, padx=20, pady=20,
    bg=panel_color, bd=4, relief="solid",
    highlightbackground=neon_green, highlightthickness=2
)
control_frame.grid(row=0, column=1, sticky="n")

Label(
    control_frame,
    text="EVA CONTROL PANEL",
    font=("Consolas", 18, "bold"),
    fg=neon_orange,
    bg=panel_color
).grid(row=0, column=0, columnspan=3, pady=(0, 5))

Label(
    control_frame,
    text="SYSTEM STATUS: NORMAL",
    font=("Consolas", 10, "bold"),
    fg=neon_green,
    bg=panel_color
).grid(row=1, column=0, columnspan=3, pady=(0, 10))

# ================================================================
# MODO MANUAL
# ================================================================
manual_var = BooleanVar(value=False)

def toggle_manual():
    global manual_mode, latest_left_code, latest_left_name, latest_right_code, latest_right_name
    manual_mode = manual_var.get()
    # Al activar modo manual, ponemos ambos brazos en Quieto
    if manual_mode:
        with gesture_lock:
            latest_left_code = "1"
            latest_left_name = "Quieto"
            latest_right_code = "1"
            latest_right_name = "Quieto"

manual_check = Checkbutton(
    control_frame,
    text="Modo manual (No envia gestos automáticos)",
    variable=manual_var,
    command=toggle_manual,
    fg=neon_green,
    bg=panel_color,
    selectcolor=panel_color,
    font=("Consolas", 11),
    activebackground=panel_color,
    activeforeground=neon_green
)
manual_check.grid(row=2, column=0, columnspan=3, pady=10)

# ================================================================
# PANEL MANUAL 1 (SERVOS 1 Y 2) - MOVIMIENTOS LINEALES
# ================================================================
lineal_frame = Frame(control_frame, bg=panel_color)
lineal_frame.grid(row=3, column=0, columnspan=3, pady=(5, 10))

Label(
    lineal_frame,
    text="MOVIMIENTOS LINEALES (Servos 1 y 2)",
    font=("Consolas", 11, "bold"),
    fg=neon_blue,
    bg=panel_color
).grid(row=0, column=0, columnspan=3, pady=(0, 5))

def set_left_manual(code, name):
    global latest_left_code, latest_left_name
    if not manual_mode:
        return
    with gesture_lock:
        latest_left_code = code
        latest_left_name = name

def reset_left(event=None):
    global latest_left_code, latest_left_name
    if not manual_mode:
        return
    with gesture_lock:
        latest_left_code = "1"
        latest_left_name = "Quieto"

def make_dpad_button(parent, text):
    return Button(
        parent,
        text=text,
        width=8,
        height=1,
        bg=button_bg,
        fg=neon_purple,
        activebackground="#261b3a",
        activeforeground=neon_blue,
        highlightbackground=button_border,
        highlightthickness=2,
        bd=0,
        font=("Consolas", 10, "bold"),
        relief="flat"
    )

# Cruceta lineal
btn_lin_up = make_dpad_button(lineal_frame, "ADELANTE")
btn_lin_left = make_dpad_button(lineal_frame, "IZQ")
btn_lin_center = make_dpad_button(lineal_frame, "QUIETO")
btn_lin_right = make_dpad_button(lineal_frame, "DER")
btn_lin_down = make_dpad_button(lineal_frame, "ATRAS")

btn_lin_up.grid(row=1, column=1, pady=2)
btn_lin_left.grid(row=2, column=0, padx=2, pady=2)
btn_lin_center.grid(row=2, column=1, padx=2, pady=2)
btn_lin_right.grid(row=2, column=2, padx=2, pady=2)
btn_lin_down.grid(row=3, column=1, pady=2)

# Bindings brazo izquierdo
btn_lin_up.bind("<ButtonPress-1>",   lambda e: set_left_manual("2", "Adelante"))
btn_lin_left.bind("<ButtonPress-1>", lambda e: set_left_manual("3", "Izquierda"))
btn_lin_right.bind("<ButtonPress-1>",lambda e: set_left_manual("4", "Derecha"))
btn_lin_down.bind("<ButtonPress-1>", lambda e: set_left_manual("5", "Atras"))
btn_lin_center.bind("<ButtonPress-1>", lambda e: set_left_manual("1", "Quieto"))

btn_lin_up.bind("<ButtonRelease-1>",     reset_left)
btn_lin_left.bind("<ButtonRelease-1>",   reset_left)
btn_lin_right.bind("<ButtonRelease-1>",  reset_left)
btn_lin_down.bind("<ButtonRelease-1>",   reset_left)
btn_lin_center.bind("<ButtonRelease-1>", reset_left)

# ================================================================
# PANEL MANUAL 2 (SERVOS 3 Y 4) - ROTACIONES
# ================================================================
rot_frame = Frame(control_frame, bg=panel_color)
rot_frame.grid(row=4, column=0, columnspan=3, pady=(5, 10))

Label(
    rot_frame,
    text="ROTACIONES (Servos 3 y 4)",
    font=("Consolas", 11, "bold"),
    fg=neon_green,
    bg=panel_color
).grid(row=0, column=0, columnspan=3, pady=(0, 5))

def set_right_manual(code, name):
    global latest_right_code, latest_right_name
    if not manual_mode:
        return
    with gesture_lock:
        latest_right_code = code
        latest_right_name = name

def reset_right(event=None):
    global latest_right_code, latest_right_name
    if not manual_mode:
        return
    with gesture_lock:
        latest_right_code = "1"
        latest_right_name = "Quieto"

btn_rot_up = make_dpad_button(rot_frame, "ARRIBA")
btn_rot_left = make_dpad_button(rot_frame, "IZQ")
btn_rot_center = make_dpad_button(rot_frame, "QUIETO")
btn_rot_right = make_dpad_button(rot_frame, "DER")
btn_rot_down = make_dpad_button(rot_frame, "ABAJO")

btn_rot_up.grid(row=1, column=1, pady=2)
btn_rot_left.grid(row=2, column=0, padx=2, pady=2)
btn_rot_center.grid(row=2, column=1, padx=2, pady=2)
btn_rot_right.grid(row=2, column=2, padx=2, pady=2)
btn_rot_down.grid(row=3, column=1, pady=2)

# Bindings brazo derecho
btn_rot_up.bind("<ButtonPress-1>",    lambda e: set_right_manual("2", "Arriba"))
btn_rot_left.bind("<ButtonPress-1>",  lambda e: set_right_manual("3", "Izquierda"))
btn_rot_right.bind("<ButtonPress-1>", lambda e: set_right_manual("4", "Derecha"))
btn_rot_down.bind("<ButtonPress-1>",  lambda e: set_right_manual("5", "Abajo"))
btn_rot_center.bind("<ButtonPress-1>",lambda e: set_right_manual("1", "Quieto"))

btn_rot_up.bind("<ButtonRelease-1>",     reset_right)
btn_rot_left.bind("<ButtonRelease-1>",   reset_right)
btn_rot_right.bind("<ButtonRelease-1>",  reset_right)
btn_rot_down.bind("<ButtonRelease-1>",   reset_right)
btn_rot_center.bind("<ButtonRelease-1>", reset_right)

# ================================================================
# RETROALIMENTACION DE AMBOS BRAZOS
# ================================================================
feedback_label = Label(
    control_frame,
    text="Brazo izq: Quieto | Brazo der: Quieto [Auto]",
    font=("Consolas", 12),
    fg=neon_blue,
    bg=panel_color,
    justify="left"
)
feedback_label.grid(row=5, column=0, columnspan=3, pady=10)

# ================================================================
# ESTADO DE CONEXION
# ================================================================
status_frame = Frame(control_frame, bg=panel_color)
status_frame.grid(row=6, column=0, columnspan=3, pady=10)

status_light = Label(status_frame, text="●", font=("Consolas", 22),
                     fg=neon_red, bg=panel_color)
status_light.grid(row=0, column=0)

status_text = Label(status_frame, text="LINK: OFFLINE",
                    font=("Consolas", 12, "bold"),
                    fg=text_color, bg=panel_color)
status_text.grid(row=0, column=1, padx=10)

btn_connect = Button(
    status_frame,
    text="CONECTAR",
    width=12,
    bg=button_bg,
    fg=neon_blue,
    font=("Consolas", 11, "bold"),
    highlightbackground=neon_blue,
    highlightthickness=2,
    bd=0
)
btn_connect.grid(row=0, column=2, padx=10)

# ================================================================
# TUTORIAL DENTRO DE LA VENTANA PRINCIPAL
# ================================================================
tutorial_container = Frame(main_frame, bg=bg_color)
tutorial_container.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(15, 0))
main_frame.grid_rowconfigure(1, weight=1)

tutorial_visible = False

def construir_tutorial(parent):
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    canvas = Canvas(parent, bg=bg_color, highlightthickness=0)
    scrollbar = Scrollbar(parent, orient="vertical", command=canvas.yview)
    scroll_frame = Frame(canvas, bg=bg_color)

    scroll_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    figuras = [
        ("fig1_quieto.png", "Quieto",
         "Postura neutral con ambos brazos abajo."),

        ("fig2_izquierda.png", "Brazo izquierdo a la izquierda",
         "Extiende brazo izquierdo hacia el lado izquierdo."),

        ("fig3_derecha.png", "Brazo derecho a la derecha",
         "Extiende brazo derecho hacia el lado derecho."),

        ("fig4_adelante.png", "Adelante",
         "Saludo militar con brazo derecho."),

        ("fig5_atras.png", "Atrás",
         "Flexiona brazo izquierdo al hombro.")
    ]

    parent.images = []

    title_lbl = Label(scroll_frame,
        text="Tutorial de Posturas - EVA LINK",
        font=("Consolas", 16, "bold"),
        fg=neon_orange, bg=bg_color
    )
    title_lbl.pack(pady=(5, 15))

    for filename, titulo, desc in figuras:

        card = Frame(scroll_frame, bg=panel_color, bd=2,
                     highlightbackground=neon_purple, highlightthickness=2)
        card.pack(padx=20, pady=10, fill="x")

        full_path = os.path.join(BASE_DIR, filename)

        try:
            img_cv = cv2.imread(full_path)
            if img_cv is None:
                raise Exception()

            img_cv = cv2.resize(img_cv, (200, 200))
            img_cv = cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB)
            img = ImageTk.PhotoImage(Image.fromarray(img_cv))
            parent.images.append(img)

            img_label = Label(card, image=img, bg=panel_color)
            img_label.pack(pady=(10, 5))

        except:
            Label(card, text=f"[No se encontró {filename}]",
                  fg=neon_red, bg=panel_color,
                  font=("Consolas", 10, "italic")).pack()

        Label(card, text=titulo,
              font=("Consolas", 13, "bold"),
              fg=neon_green, bg=panel_color).pack(pady=(0, 5))

        Label(card, text=desc, wraplength=640,
              justify="left",
              font=("Consolas", 11),
              fg=text_color, bg=panel_color).pack(padx=10, pady=(0, 10))

def toggle_tutorial():
    global tutorial_visible
    for w in tutorial_container.winfo_children():
        w.destroy()

    if tutorial_visible:
        tutorial_visible = False
        btn_tutorial.config(text="ABRIR TUTORIAL")
    else:
        construir_tutorial(tutorial_container)
        tutorial_visible = True
        btn_tutorial.config(text="OCULTAR TUTORIAL")

btn_tutorial = Button(
    control_frame,
    text="ABRIR TUTORIAL",
    command=toggle_tutorial,
    width=28,
    bg=button_bg,
    fg=neon_green,
    font=("Consolas", 11, "bold"),
    highlightbackground=neon_green,
    highlightthickness=2,
    bd=0
)
btn_tutorial.grid(row=7, column=0, columnspan=3, pady=(5, 5))

# ================================================================
# CONEXION ESP32
# ================================================================
def toggle_connection():
    global client, connected

    if connected:
        try: client.close()
        except: pass
        connected = False
    else:
        try:
            c = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            c.settimeout(1)
            c.connect((ESP32_IP, PORT))
            client = c
            connected = True
        except:
            client = None
            connected = False

btn_connect.config(command=toggle_connection)

# ================================================================
# HILO ENVIO
# ================================================================
def communication_thread():
    global client, connected, running
    global latest_left_code, latest_right_code

    while running:
        if connected and client:
            try:
                msg = f"{latest_left_code},{latest_right_code}\n"
                client.send(msg.encode())
            except:
                connected = False

        time.sleep(0.05)

# ================================================================
# CAMARA
# ================================================================
def camera_thread():
    global latest_frame, running

    cap = cv2.VideoCapture(0)
    cap.set(3, 640)
    cap.set(4, 360)

    if not cap.isOpened():
        print("No se pudo abrir la camara.")
        running = False
        return

    while running:
        ret, frame = cap.read()
        if ret:
            with frame_lock:
                latest_frame = frame
        time.sleep(0.01)

    cap.release()

# ================================================================
# DETECCION MEDIAPIPE PARA AMBOS BRAZOS
# ================================================================
def detection_thread():
    global latest_left_code, latest_left_name
    global latest_right_code, latest_right_name
    global manual_mode

    def detect_arm_positions_side(lm, side="left"):
        if side == "left":
            shoulder = lm[11]
            wrist = lm[15]
        else:
            shoulder = lm[12]
            wrist = lm[16]

        dy = wrist.y - shoulder.y
        dx = wrist.x - shoulder.x

        if abs(dy) < 0.05 and abs(dx) < 0.05:
            return "5", "Atras"
        elif dy < -0.1 and abs(dx) < 0.1:
            return "2", "Adelante"
        elif dx < -0.15:
            return "4", "Derecha"
        elif dx > 0.15:
            return "3", "Izquierda"
        else:
            return "1", "Quieto"

    with mp_pose.Pose(
        model_complexity=0,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    ) as pose:

        while running:
            if latest_frame is None or manual_mode:
                time.sleep(0.02)
                continue

            with frame_lock:
                frame = latest_frame.copy()

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = pose.process(rgb)

            if results.pose_landmarks:
                lm = results.pose_landmarks.landmark

                codeL, nameL = detect_arm_positions_side(lm, "left")
                codeR, nameR = detect_arm_positions_side(lm, "right")

                with gesture_lock:
                    latest_left_code = codeL
                    latest_left_name = nameL
                    latest_right_code = codeR
                    latest_right_name = nameR

            time.sleep(0.02)

# ================================================================
# UPDATE GUI
# ================================================================
def update_gui():
    if latest_frame is not None:
        with frame_lock:
            frame = latest_frame.copy()

        with gesture_lock:
            left_name = latest_left_name
            left_code = latest_left_code
            right_name = latest_right_name
            right_code = latest_right_code

        cv2.putText(frame, f"L: {left_name} ({left_code})", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 120, 255), 2)
        cv2.putText(frame, f"R: {right_name} ({right_code})", (10, 55),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (120, 255, 200), 2)

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        imgtk = ImageTk.PhotoImage(Image.fromarray(frame))
        camera_label.config(image=imgtk)
        camera_label.imgtk = imgtk

    if connected:
        status_light.config(fg=neon_green)
        status_text.config(text="LINK: ONLINE")
        btn_connect.config(text="DESCONECTAR")
    else:
        status_light.config(fg=neon_red)
        status_text.config(text="LINK: OFFLINE")
        btn_connect.config(text="CONECTAR")

    with gesture_lock:
        feedback_label.config(
            text=f"Brazo izq: {latest_left_name} | Brazo der: {latest_right_name} [{'Manual' if manual_mode else 'Auto'}]"
        )

    if running:
        root.after(50, update_gui)

# ================================================================
# HILOS
# ================================================================
threading.Thread(target=camera_thread, daemon=True).start()
threading.Thread(target=communication_thread, daemon=True).start()
threading.Thread(target=detection_thread, daemon=True).start()

update_gui()
root.mainloop()
running = False
