#include <WiFi.h>
#include <ESP32Servo.h>

// ================================================================
// ⚙️ CONFIGURACIÓN WiFi
// ================================================================
const char* ssid = "aterm-fdad69-g";
const char* password = "42c626d4182b8";

WiFiServer server(12345);

// ================================================================
// ⚙️ CONFIGURACIÓN DE SERVOS
// ================================================================
Servo servo1, servo2, servo3, servo4, servo5, servo6;

// Pines asignados
const int pin1 = 13;  // Brazo izquierdo - Servo 1
const int pin2 = 12;  // Brazo izquierdo - Servo 2
const int pin3 = 25;  // Brazo derecho - Servo 3
const int pin4 = 26;  // Brazo derecho - Servo 4
const int pin5 = 27;  // Extra (no usado)
const int pin6 = 14;  // Extra (no usado)

// ================================================================
// 🦾 FUNCIONES DE MOVIMIENTO
// ================================================================
void moverBrazoIzquierdo(int s1, int s2) {
  servo1.write(constrain(s1, 0, 180));
  servo2.write(constrain(s2, 0, 180));
  Serial.printf("🦾 Brazo IZQUIERDO → [%d, %d]\n", s1, s2);
}

void moverBrazoDerecho(int s3, int s4) {
  servo3.write(constrain(s3, 0, 180));
  servo4.write(constrain(s4, 0, 180));
  Serial.printf("🤖 Brazo DERECHO → [%d, %d]\n", s3, s4);
}

// ================================================================
// 🔧 FUNCIONES AUXILIARES
// ================================================================
bool esGestoIzquierdo(int g) { return (g >= 1 && g <= 5); }
bool esGestoDerecho(int g) { return (g >= 6 && g <= 11); }

// ================================================================
// 🔧 SETUP
// ================================================================
void setup() {
  Serial.begin(115200);
  delay(500);

  servo1.attach(pin1);
  servo2.attach(pin2);
  servo3.attach(pin3);
  servo4.attach(pin4);
  servo5.attach(pin5);
  servo6.attach(pin6);

  // Posición inicial
  moverBrazoIzquierdo(30, 150);
  moverBrazoDerecho(110, 110);
  servo5.write(90);
  servo6.write(90);

  // Conexión WiFi
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

// ================================================================
// 🔁 LOOP PRINCIPAL
// ================================================================
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

        Serial.print("📩 Datos recibidos: ");
        Serial.println(data);

        int gesture = data.toInt();
        
        // --- Validar que el gesto sea un número válido (1-11) ---
        if (gesture == 0 && data != "0") {
          Serial.println("⚠️ Gesto inválido: no es un número válido");
          client.println("Error: gesto inválido - no es un número");
          continue;
        }
        
        if (gesture < 1 || gesture > 11) {
          Serial.println("⚠️ Gesto fuera de rango (debe ser 1-11)");
          client.println("Error: gesto fuera de rango");
          continue;
        }

        // --- Seguridad: evitar gestos simultáneos ---
        // El gesto 11 es especial: regreso a home, siempre permitido
        bool esIzq = esGestoIzquierdo(gesture);
        bool esDer = esGestoDerecho(gesture);

        // El gesto 11 puede ejecutarse siempre (es un comando de reset/home)
        if (gesture != 11) {
          if ((esIzq && ultimoGestoDer != 8) || (esDer && ultimoGestoIzq != 1)) {
            Serial.println("⚠️ Movimiento simultáneo no permitido");
            client.println("⚠️ Movimiento simultáneo no permitido");
            continue;
          }
        }

        // --- Actualizar estado ---
        if (gesture == 11) {
          // El gesto 11 resetea ambos brazos a quieto
          ultimoGestoIzq = 1;
          ultimoGestoDer = 8;
        } else {
          if (esIzq) ultimoGestoIzq = gesture;
          if (esDer) ultimoGestoDer = gesture;
        }

        // --- Acciones por gesto ---
        switch (gesture) {
          // ==== BRAZO IZQUIERDO ====
          case 1: moverBrazoIzquierdo(30, 150); moverBrazoDerecho(110, 110); client.println("OK 1 Quieto"); break;
          case 2: moverBrazoIzquierdo(0, 0); moverBrazoDerecho(110, 110); client.println("OK 2 Arriba"); break;
          case 3: moverBrazoIzquierdo(0, 180); moverBrazoDerecho(110, 110); client.println("OK 3 Izquierda"); break;
          case 4: moverBrazoIzquierdo(90, 90); moverBrazoDerecho(110, 110); client.println("OK 4 Derecha"); break;
          case 5: moverBrazoIzquierdo(180, 180); moverBrazoDerecho(110, 110); client.println("OK 5 Abajo"); break;

          // ==== BRAZO DERECHO ====
          case 6: moverBrazoIzquierdo(30, 150); moverBrazoDerecho(90, 145); client.println("OK 6 Rotación derecha"); break;
          case 7: moverBrazoIzquierdo(30, 150); moverBrazoDerecho(180, 0); client.println("OK 7 Rotación izquierda"); break;
          case 8: moverBrazoIzquierdo(30, 150); moverBrazoDerecho(110, 110); client.println("OK 8 Quieto derecho"); break;
          case 9: moverBrazoIzquierdo(30, 150); moverBrazoDerecho(150, 110); client.println("OK 9 Rotación arriba"); break;
          case 10: moverBrazoIzquierdo(30, 150); moverBrazoDerecho(0, 0); client.println("OK 10 Rotación abajo"); break;

          // ==== NUEVO CASO 11 ====
          case 11:
            moverBrazoIzquierdo(30, 150);
            moverBrazoDerecho(110, 110);
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
