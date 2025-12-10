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
ESP32_IP = "192.168.10.175"
PORT = 12345

# ================================================================
# 🧠 VARIABLES GLOBALES
# ================================================================
mp_pose = mp.solutions.pose
frame_lock = threading.Lock()
gesture_lock = threading.Lock()

latest_frame = None
latest_gesture = "1"
running = True
client_socket = None
connected = False
invalid_motion_flag = False   # 🚨 Nueva bandera de interrupción
invalid_lock = threading.Lock()

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
# 🧠 DETECCIÓN DE GESTOS Y LÓGICA GLOBAL
# ================================================================
def detection_thread():
    global latest_frame, latest_gesture, running, connected, invalid_motion_flag

    def detect_left_arm(lm):
        left_shoulder = lm[11]
        left_wrist = lm[15]
        dy = left_wrist.y - left_shoulder.y
        dx = left_wrist.x - left_shoulder.x
        if abs(dx) < 0.1 and dy > 0.05: return 1   # Quieto
        elif dy < -0.1 and abs(dx) < 0.1: return 2 # Arriba
        elif dx < -0.15: return 3                  # Izquierda
        elif dx > 0.15: return 4                   # Derecha
        elif abs(dy) < 0.05 and abs(dx) < 0.05: return 5 # Abajo
        return 1

    def detect_right_arm(lm):
        right_shoulder = lm[12]
        right_wrist = lm[16]
        dy = right_wrist.y - right_shoulder.y
        dx = right_wrist.x - right_shoulder.x
        if dy > 0.05 and abs(dx) < 0.1: return 8   # Quieto
        elif dx > 0.15: return 6                   # Rot. derecha
        elif dx < -0.15: return 7                  # Rot. izquierda
        elif dy < -0.1 and abs(dx) < 0.1: return 9 # Rot. arriba
        elif abs(dy) < 0.05 and abs(dx) < 0.05: return 10 # Rot. abajo
        return 8

    gesture_names_left = {
        1: "Quieto", 2: "Arriba", 3: "Izquierda", 4: "Derecha", 5: "Abajo"
    }
    gesture_names_right = {
        6: "Rot. derecha", 7: "Rot. izquierda", 8: "Quieto",
        9: "Rot. arriba", 10: "Rot. abajo"
    }

    def disable_invalid_flag_after_delay(delay=2):
        """⏳ Desactiva la interrupción después del tiempo indicado."""
        global invalid_motion_flag
        time.sleep(delay)
        with invalid_lock:
            invalid_motion_flag = False
        print("✅ Interrupción de movimiento inválido desactivada.")

    with mp_pose.Pose(model_complexity=0,
                      min_detection_confidence=0.5,
                      min_tracking_confidence=0.5) as pose:

        print("🧠 Detección iniciada (Quieto Global Inteligente).")

        left_gesture = 1
        right_gesture = 8
        last_sent = None

        while running:
            with frame_lock:
                if latest_frame is None:
                    continue
                frame_original = latest_frame.copy()

            image_rgb = cv2.cvtColor(frame_original, cv2.COLOR_BGR2RGB)
            results = pose.process(image_rgb)
            frame_display = cv2.flip(frame_original, 1)

            gesture_to_send = None
            warning_text = ""

            if results.pose_landmarks:
                lm = results.pose_landmarks.landmark
                left_gesture = detect_left_arm(lm)
                right_gesture = detect_right_arm(lm)

                # ==================================================
                # 🔍 LÓGICA GLOBAL SEGÚN TABLA DE VERDAD
                # ==================================================
                if left_gesture == 1 and right_gesture == 8:
                    gesture_to_send = "QUIETO_TOTAL"
                elif left_gesture != 1 and right_gesture == 8:
                    gesture_to_send = str(left_gesture)
                elif left_gesture == 1 and right_gesture != 8:
                    gesture_to_send = str(right_gesture)
                else:
                    warning_text = "⚠️ Movimiento inválido — interrupción activada"
                    gesture_to_send = None

                    # 🚨 Activar bandera de interrupción
                    with invalid_lock:
                        if not invalid_motion_flag:
                            invalid_motion_flag = True
                            print("🚨 Interrupción activada por movimiento inválido.")
                            threading.Thread(target=disable_invalid_flag_after_delay, daemon=True).start()

                # ==================================================
                # 🔁 Reforzar HOME del brazo derecho
                # ==================================================
                if right_gesture == 8 and last_sent not in ("8", "11", "QUIETO_TOTAL"):
                    gesture_to_send = "11"  # Forzar posición 3=110°,4=110°

                # ==================================================
                # 💬 VISUALIZACIÓN
                # ==================================================
                left_text = f"🦾 Izquierdo: {gesture_names_left.get(left_gesture)}"
                right_text = f"💪 Derecho: {gesture_names_right.get(right_gesture)}"
                conn_text = "🟢 Conectado" if connected else "🔴 Sin conexión"
                color_conn = (0, 255, 0) if connected else (0, 0, 255)

                cv2.putText(frame_display, left_text, (20, 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
                cv2.putText(frame_display, right_text, (20, 80),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
                cv2.putText(frame_display, conn_text, (20, 120),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, color_conn, 2)

                if warning_text:
                    cv2.putText(frame_display, warning_text, (40, 160),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

                last_sent = gesture_to_send if gesture_to_send else last_sent
                with gesture_lock:
                    latest_gesture = gesture_to_send if gesture_to_send else "0"

            cv2.imshow("Teleoperación ESP32 - Quieto global inteligente", frame_display)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                running = False
                break

        cv2.destroyAllWindows()

# ================================================================
# 📡 FUNCIÓN DE ENVÍO AL ESP32
# ================================================================
def send_to_esp32(message):
    global client_socket
    try:
        if client_socket:
            client_socket.send((message + "\n").encode())
    except Exception as e:
        print(f"⚠️ Error enviando '{message}':", e)

# ================================================================
# 📡 HILO 3 — COMUNICACIÓN CON REINTENTOS
# ================================================================
def communication_thread():
    global latest_gesture, running, client_socket, connected, invalid_motion_flag
    SEND_INTERVAL = 0.1
    RECONNECT_INTERVAL = 5

    connected = False
    last_sent = None

    while running:
        if not connected:
            try:
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_socket.settimeout(2)
                client_socket.connect((ESP32_IP, PORT))
                connected = True
                print(f"✅ Conectado al ESP32 ({ESP32_IP}:{PORT})")
            except Exception:
                print(f"⚠️ No se pudo conectar con ESP32 ({ESP32_IP}). Reintentando en {RECONNECT_INTERVAL}s...")
                time.sleep(RECONNECT_INTERVAL)
                continue

        try:
            time.sleep(SEND_INTERVAL)
            with gesture_lock:
                current = latest_gesture

            # 🚨 Si hay una interrupción activa, no enviar nada
            with invalid_lock:
                if invalid_motion_flag:
                    continue

            if not current or current == "0" or current == last_sent:
                continue

            client_socket.send((current + "\n").encode())
            last_sent = current

            try:
                response = client_socket.recv(1024).decode().strip()
                if response:
                    print(f"📤 Enviado: {current} | 📥 {response}")
            except socket.timeout:
                pass

        except Exception as e:
            print("❌ Conexión con ESP32 perdida. Intentando reconectar...")
            connected = False
            last_sent = None
            try:
                client_socket.close()
            except:
                pass
            time.sleep(RECONNECT_INTERVAL)

    try:
        client_socket.close()
    except:
        pass
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
