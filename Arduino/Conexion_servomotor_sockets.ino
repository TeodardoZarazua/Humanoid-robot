#include <WiFi.h>
#include <ESP32Servo.h>   // Librería compatible con ESP32

// --- Configuración WiFi ---
const char* ssid = "aterm-fdad69-g";     // ⚠️ Tu red WiFi
const char* password = "42c626d4182b8";  // ⚠️ Contraseña WiFi

WiFiServer server(12345); // Puerto TCP

// --- Configuración de Servos ---
Servo servo1, servo2, servo3, servo4, servo5, servo6;

// Pines asignados
const int pin1 = 13;
const int pin2 = 12;
const int pin3 = 14;
const int pin4 = 27;
const int pin5 = 26;
const int pin6 = 25;

// --- Función para mover servos con impresión ---
void moverServos(int s1, int s2, int s3, int s4) {
  servo1.write(constrain(s1, 0, 180));
  servo2.write(constrain(s2, 0, 180));
  servo3.write(constrain(s3, 0, 180));
  servo4.write(constrain(s4, 0, 180));

  Serial.printf("🎯 Servos → [%d, %d, %d, %d]\n", s1, s2, s3, s4);
}

// --- Funciones auxiliares ---
bool esGestoIzquierdo(int g) { return (g >= 1 && g <= 5); }
bool esGestoDerecho(int g) { return (g >= 6 && g <= 11); }

// --- SETUP ---
void setup() {
  Serial.begin(115200);
  delay(500);

  // Adjuntar servos
  servo1.attach(pin1);
  servo2.attach(pin2);
  servo3.attach(pin3);
  servo4.attach(pin4);
  servo5.attach(pin5);
  servo6.attach(pin6);

  // Posición inicial (Quieto total)
  moverServos(30, 150, 110, 110);
  servo5.write(90);
  servo6.write(90);

  // --- Conexión WiFi ---
  WiFi.begin(ssid, password);
  Serial.print("Conectando a WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\n✅ Conectado a WiFi");
  Serial.print("IP del ESP32: ");
  Serial.println(WiFi.localIP());

  server.begin();
  Serial.println("Servidor TCP iniciado ✅");
}

// --- LOOP ---
void loop() {
  WiFiClient client = server.available();

  if (client) {
    Serial.println("💻 Cliente conectado");

    int ultimoGestoIzq = 1;  // Quieto
    int ultimoGestoDer = 8;  // Quieto

    while (client.connected()) {
      if (client.available()) {
        String data = client.readStringUntil('\n');
        data.trim();
        if (data.length() == 0) continue;

        Serial.print("📩 Gesto recibido: ");
        Serial.println(data);

        int gesture = data.toInt();

        // --- Seguridad: evitar gestos simultáneos ---
        bool esIzq = esGestoIzquierdo(gesture);
        bool esDer = esGestoDerecho(gesture);

        if ((esIzq && ultimoGestoDer != 8) || (esDer && ultimoGestoIzq != 1)) {
          Serial.println("⚠️ Movimiento simultáneo no permitido");
          client.println("⚠️ Movimiento simultáneo no permitido");
          continue;
        }

        // --- Actualizar estado ---
        if (esIzq) ultimoGestoIzq = gesture;
        if (esDer) ultimoGestoDer = gesture;

        // --- Acciones por gesto ---
        switch (gesture) {
          // ==== BRAZO IZQUIERDO ====
          case 1: moverServos(30, 150, 110, 110); client.println("OK 1 Quieto"); break;
          case 2: moverServos(0, 0, 110, 110); client.println("OK 2 Arriba"); break;
          case 3: moverServos(0, 180, 110, 110); client.println("OK 3 Izquierda"); break;
          case 4: moverServos(90, 90, 110, 110); client.println("OK 4 Derecha"); break;
          case 5: moverServos(180, 180, 110, 110); client.println("OK 5 Abajo"); break;

          // ==== BRAZO DERECHO ====
          case 6: moverServos(30, 150, 90, 145); client.println("OK 6 Rotación derecha"); break;
          case 7: moverServos(30, 150, 180, 0); client.println("OK 7 Rotación izquierda"); break;
          case 8: moverServos(30, 150, 110, 110); client.println("OK 8 Quieto derecho"); break;
          case 9: moverServos(30, 150, 150, 110); client.println("OK 9 Rotación arriba"); break;
          case 10: moverServos(30, 150, 0, 0); client.println("OK 10 Rotación abajo"); break;

          // ==== NUEVO CASO 11 ====
          case 11:
            moverServos(30, 150, 110, 110);
            client.println("OK 11 Regreso a home (3=110, 4=110)");
            Serial.println("🔁 Brazo derecho forzado a posición central (home)");
            break;

          default:
            Serial.println("⚠️ Gesto no reconocido");
            client.println("Error: gesto inválido");
            break;
        }
      }
    }

    client.stop();
    Serial.println("❌ Cliente desconectado");
  }
}
