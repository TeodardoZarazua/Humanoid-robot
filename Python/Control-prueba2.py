import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

import cv2
import mediapipe as mp
import socket
import time
import threading

# ================================================================
# ⚙️ CONFIGURACIÓN DEL SERVIDOR (ESP32)
# ================================================================
ESP32_IP = "192.168.10.175"   # ⚠️ Cambia por la IP de tu ESP32
PORT = 12345

# ================================================================
# 🧠 VARIABLES GLOBALES
# ================================================================
mp_pose = mp.solutions.pose
frame_lock = threading.Lock()
gesture_lock = threading.Lock()

latest_frame = None
right_gesture = "R1"   # Brazo derecho
left_gesture = "L1"    # Brazo izquierdo
running = True

# ================================================================
# 🎥 HILO 1 — CAPTURA DE CÁMARA
# ================================================================
def camera_thread():
    global latest_frame, running
    cap = cv2.VideoCapture(0)
    cap.set(3, 640)
    cap.set(4, 360)

    if not cap.isOpened():
        print("❌ No se pudo abrir la cámara.")
        running = False
        return

    print("📸 Cámara iniciada.")
    while running:
        ret, frame = cap.read()
        if not ret:
            continue

        with frame_lock:
            latest_frame = frame
    cap.release()
    print("📴 Cámara detenida.")

# ================================================================
# 🧠 HILO 2 — DETECCIÓN DE GESTOS (AMBOS BRAZOS)
# ================================================================
def detection_thread():
    global latest_frame, right_gesture, left_gesture, running

    def detect_right_arm(lm):
        shoulder = lm[12]
        wrist = lm[16]
        dy = wrist.y - shoulder.y
        dx = wrist.x - shoulder.x

        if abs(dy) < 0.05 and abs(dx) < 0.05:
            return "R5"  # Abajo
        elif dy < -0.1 and abs(dx) < 0.1:
            return "R2"  # Arriba
        elif dx < -0.15:
            return "R3"  # Izquierda
        elif dx > 0.15:
            return "R4"  # Derecha
        elif abs(dx) < 0.1 and dy > 0.05:
            return "R1"  # Centro
        return right_gesture

    def detect_left_arm(lm):
        shoulder = lm[11]
        wrist = lm[15]
        dy = wrist.y - shoulder.y
        dx = wrist.x - shoulder.x

        if abs(dy) < 0.05 and abs(dx) < 0.05:
            return "L5"  # Atrás
        elif dy < -0.1 and abs(dx) < 0.1:
            return "L2"  # Arriba
        elif dx < -0.15:
            return "L3"  # Izquierda
        elif dx > 0.15:
            return "L4"  # Derecha
        elif abs(dx) < 0.1 and dy > 0.05:
            return "L1"  # Centro
        return left_gesture

    with mp_pose.Pose(
        model_complexity=0,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    ) as pose:
        print("🧠 Detección iniciada (ambos brazos).")
        while running:
            with frame_lock:
                if latest_frame is None:
                    continue
                frame_original = latest_frame.copy()

            image_rgb = cv2.cvtColor(frame_original, cv2.COLOR_BGR2RGB)
            results = pose.process(image_rgb)
            frame_display = cv2.flip(frame_original, 1)

            if results.pose_landmarks:
                lm = results.pose_landmarks.landmark
                new_right = detect_right_arm(lm)
                new_left = detect_left_arm(lm)

                with gesture_lock:
                    right_gesture = new_right
                    left_gesture = new_left

                # Mostrar texto en pantalla
                cv2.putText(frame_display, f"{new_right}", (20, 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
                cv2.putText(frame_display, f"{new_left}", (20, 80),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 150, 0), 2)

            cv2.imshow("Teleoperación ESP32 - Ambos brazos", frame_display)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                running = False
                break

        cv2.destroyAllWindows()
        print("🧠 Detección detenida.")

# ================================================================
# 📡 HILO 3 — COMUNICACIÓN CON ESP32
# ================================================================
def communication_thread():
    global right_gesture, left_gesture, running
    SEND_INTERVAL = 0.1  # 10 Hz

    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(0.1)
        client.connect((ESP32_IP, PORT))
        print(f"✅ Conectado al ESP32 ({ESP32_IP}:{PORT})")
    except Exception as e:
        print("❌ Error de conexión con ESP32:", e)
        running = False
        return

    last_right = None
    last_left = None

    while running:
        time.sleep(SEND_INTERVAL)

        with gesture_lock:
            r_now = right_gesture
            l_now = left_gesture

        # --- Solo enviar si cambió el gesto ---
        if r_now != last_right:
            try:
                packet = f"{r_now},L0\n"
                client.send(packet.encode())
                print(f"📤 Enviado (derecho): {r_now}")
                last_right = r_now
            except Exception as e:
                print("⚠️ Error al enviar brazo derecho:", e)
                break

        if l_now != last_left:
            try:
                packet = f"R0,{l_now}\n"
                client.send(packet.encode())
                print(f"📤 Enviado (izquierdo): {l_now}")
                last_left = l_now
            except Exception as e:
                print("⚠️ Error al enviar brazo izquierdo:", e)
                break

    client.close()
    print("🔌 Comunicación cerrada.")

# ================================================================
# 🚀 PROGRAMA PRINCIPAL
# ================================================================
if __name__ == "__main__":
    t1 = threading.Thread(target=camera_thread, daemon=True)
    t2 = threading.Thread(target=detection_thread, daemon=True)
    t3 = threading.Thread(target=communication_thread, daemon=True)

    t1.start()
    t2.start()
    t3.start()

    try:
        while running:
            time.sleep(0.05)
    except KeyboardInterrupt:
        running = False
        print("🛑 Interrupción manual. Cerrando...")

    t1.join()
    t2.join()
    t3.join()
    print("✅ Teleoperación finalizada correctamente.")
