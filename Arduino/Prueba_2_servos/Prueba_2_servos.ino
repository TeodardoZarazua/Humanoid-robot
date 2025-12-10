#include <WiFi.h>
#include <ESP32Servo.h>   // Librería compatible con ESP32

// --- Configuración WiFi ---
const char* ssid = "aterm-fdad69-g";     // ⚠ Tu red WiFi
const char* password = "42c626d4182b8";  // ⚠ Contraseña WiFi

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

  // Posición inicial (Quieto)
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

    while (client.connected()) {
      if (client.available()) {
        String data = client.readStringUntil('\n');
        data.trim();

        if (data.length() == 0) continue;

        Serial.print("📩 Gesto recibido: ");
        Serial.println(data);

        int gesture = data.toInt();

        // --- Selección del gesto ---
        switch (gesture) {
          case 1:  // Quieto
            moverServos(30, 150, 110, 110);
            client.println("OK gesto 1 (Quieto)");
            break;

          case 2:  // Avance
            moverServos(0, 0, 110, 110);
            client.println("OK gesto 2 (Avance)");
            break;

          case 3:  // Izquierda (antes Derecha)
            moverServos(90, 90, 110, 110);
            client.println("OK gesto 3 (Izquierda)");
            break;

          case 4:  // Derecha (antes Izquierda)
            moverServos(0, 180, 110, 110);
            client.println("OK gesto 4 (Derecha)");
            break;

          case 5:  // Atrás (igual que Quieto)
            moverServos(180, 180, 110, 110);
            client.println("OK gesto 5 (Atrás)");
            break;

          default:
            Serial.println("⚠ Gesto no reconocido");
            client.println("Error: gesto inválido");
            break;
        }
      }
    }

    client.stop();
    Serial.println("❌ Cliente desconectado");
  }
}