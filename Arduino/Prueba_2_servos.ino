#include <WiFi.h>
#include <ESP32Servo.h>

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

// --- Funciones para mover servos ---
void moverServosDerechos(int g) {
  switch (g) {
    case 1: servo1.write(30); servo2.write(150); break;        // Quieto
    case 2: servo1.write(0); servo2.write(0); break;           // Avance
    case 3: servo1.write(90); servo2.write(90); break;         // Izquierda
    case 4: servo1.write(0); servo2.write(180); break;         // Derecha
    case 5: servo1.write(180); servo2.write(180); break;       // Atrás
  }
}

void moverServosIzquierdos(int g) {
  switch (g) {
    case 1: servo3.write(110); servo4.write(110); break;       // Quieto
    case 2: servo3.write(150); servo4.write(170); break;       // Avance
    case 3: servo3.write(0); servo4.write(0); break;           // Izquierda
    case 4: servo3.write(40); servo4.write(145); break;        // Derecha
    case 5: servo3.write(180); servo4.write(0); break;         // Atrás
  }
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

  // Posición inicial
  moverServosDerechos(1);
  moverServosIzquierdos(1);
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

        Serial.print("📩 Datos recibidos: ");
        Serial.println(data);

        // Separar los dos valores (R,L)
        int commaIndex = data.indexOf(',');
        if (commaIndex == -1) {
          client.println("⚠️ Formato incorrecto (falta coma)");
          continue;
        }

        String rightStr = data.substring(0, commaIndex);
        String leftStr  = data.substring(commaIndex + 1);

        int gRight = rightStr.toInt();
        int gLeft  = leftStr.toInt();

        // Mover cada par de servos
        moverServosDerechos(gRight);
        moverServosIzquierdos(gLeft);

        // Feedback
        Serial.printf("🎯 R=%d | L=%d\n", gRight, gLeft);
        client.printf("OK R=%d L=%d\n", gRight, gLeft);
      }
    }

    client.stop();
    Serial.println("❌ Cliente desconectado");
  }
}
