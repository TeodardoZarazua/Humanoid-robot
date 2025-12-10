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
latest_gesture = "1"  # Por defecto (Quieto)
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

    print("📸 Cámara iniciada (sin espejo para MediaPipe).")
    while running:
        ret, frame = cap.read()
        if not ret:
            continue

        with frame_lock:
            latest_frame = frame
    cap.release()
    print("📴 Cámara detenida.")

# ================================================================
# 🧠 HILO 2 — DETECCIÓN DE GESTOS
# ================================================================
def detection_thread():
    global latest_frame, latest_gesture, running

    def detect_arm_positions(lm):
        """Evalúa las posiciones del brazo izquierdo según coordenadas reales (no espejadas)."""
        left_shoulder = lm[11]
        left_elbow = lm[13]
        left_wrist = lm[15]

        dy = left_wrist.y - left_shoulder.y
        dx = left_wrist.x - left_shoulder.x

        # --- 1: ATRÁS (antes Quieto) ---
        if abs(dy) < 0.05 and abs(dx) < 0.05:
            return "5"  # Ahora el gesto "atrás"

        # --- 2: Avance ---
        elif dy < -0.1 and abs(dx) < 0.1:
            return "2"

        # --- 3: DERECHA (antes Izquierda) ---
        elif dx < -0.15:
            return "4"

        # --- 4: IZQUIERDA (antes Derecha) ---
        elif dx > 0.15:
            return "3"

        # --- 5: QUIETO (antes Atrás) ---
        elif abs(dx) < 0.1 and dy > 0.05:
            return "1"

        return latest_gesture

    with mp_pose.Pose(
        model_complexity=0,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    ) as pose:
        print("🧠 Detección iniciada (solo espejo visual).")
        while running:
            with frame_lock:
                if latest_frame is None:
                    continue
                frame_original = latest_frame.copy()

            # Procesar sin espejo (detección precisa)
            image_rgb = cv2.cvtColor(frame_original, cv2.COLOR_BGR2RGB)
            results = pose.process(image_rgb)

            # Mostrar con espejo (solo visual)
            frame_display = cv2.flip(frame_original, 1)

            gesture = "1"
            if results.pose_landmarks:
                lm = results.pose_landmarks.landmark
                gesture = detect_arm_positions(lm)

                # Texto del gesto actualizado
                texto = {
                    "1": "🧍 Quieto",        # (Antes Atrás)
                    "2": "🚶 Avance",
                    "3": "⬅️ Izquierda",    # (Antes Derecha)
                    "4": "➡️ Derecha",      # (Antes Izquierda)
                    "5": "↩️ Atrás"         # (Antes Quieto)
                }.get(gesture, "Desconocido")

                cv2.putText(frame_display, f"Gesto: {texto}", (20, 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

            with gesture_lock:
                latest_gesture = gesture

            cv2.imshow("Teleoperación ESP32 - Vista espejo", frame_display)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                running = False
                break

        cv2.destroyAllWindows()
        print("🧠 Detección detenida.")

# ================================================================
# 📡 HILO 3 — COMUNICACIÓN CONTINUA CON ESP32
# ================================================================
def communication_thread():
    global latest_gesture, running
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

    last_sent = None
    while running:
        time.sleep(SEND_INTERVAL)
        with gesture_lock:
            current = latest_gesture

        if current != last_sent:
            try:
                client.send((current + "\n").encode())
                last_sent = current
                try:
                    response = client.recv(1024).decode().strip()
                    if response:
                        print(f"📤 Gesto {current} | 📥 {response}")
                except socket.timeout:
                    pass
            except Exception as e:
                print("⚠️ Error al enviar comando:", e)
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