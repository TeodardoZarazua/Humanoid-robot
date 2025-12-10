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
const int pin1 = 13;   // Brazo izquierdo - Servo 1
const int pin2 = 12;   // Brazo izquierdo - Servo 2
const int pin3 = 25;   // Brazo derecho - Servo 3
const int pin4 = 26;   // Brazo derecho - Servo 4
const int pin5 = 14;   // Servo 5 (Gesto A/B - PERO SE QUEDA FIJO EN 0)
const int pin6 = 27;   // Servo 6 (Gesto A/B REAL)

// ================================================================
// 🎯 CONFIG GESTOS A/B EN SERVOS 5 Y 6
// ================================================================
const int SERVO5_HOME = 180;   // Home lógico del servo 5 (NO se usa físicamente)
const int SERVO6_HOME = 90;    // Home del servo 6

// Estos eran los valores originales, pero servo5 YA NO SE MUEVE
const int SERVO5_A = 0;
const int SERVO6_A = 120;

const int SERVO5_B = 0;
const int SERVO6_B = 50;

bool gestoActivo = false;
char gestoTipo = 0;
unsigned long gestoInicio = 0;
const unsigned long GESTO_DURACION = 3000;

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
// ✨ GESTOS A Y B (MODIFICADOS PARA NO MOVER SERVO 5)
// ================================================================
void ejecutarGesto(char tipo) {
  if (gestoActivo && gestoTipo == tipo) return;

  if (tipo == 'A') {
    // servo5 NO SE MUEVE — siempre permanece en 0°
    servo6.write(SERVO6_B);
    Serial.println("✨ Gesto A ejecutado (servo5 fijo en 0°)");
  } 
  else if (tipo == 'B') {
    // servo5 NO SE MUEVE — siempre permanece en 0°
    servo6.write(SERVO6_A);
    Serial.println("✨ Gesto B ejecutado (servo5 fijo en 0°)");
  }

  gestoActivo = true;
  gestoTipo = tipo;
  gestoInicio = millis();
}

void actualizarGesto() {
  if (gestoActivo && millis() - gestoInicio >= GESTO_DURACION) {
    servo5.write(0);             // Servo5 SIEMPRE a 0°
    servo6.write(SERVO6_HOME);   // Servo6 sí regresa a home
    Serial.println("⏱ Regresando servo 6 a HOME (servo5 sigue en 0°)");
    gestoActivo = false;
    gestoTipo = 0;
  }
}

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

  // Posiciones iniciales de brazos
  moverBrazoIzquierdo(30, 150);
  moverBrazoDerecho(110, 110);

  // 🔥 Servo 5 SIEMPRE inicia y permance en 0° 🔥
  servo5.write(0);

  // Servo 6 sí tiene su home real
  servo6.write(SERVO6_HOME);

  // --------------------- WiFi --------------------------
  WiFi.begin(ssid, password);
  Serial.print("Conectando a WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\n✅ Conectado a WiFi");
  Serial.print("IP ESP32: ");
  Serial.println(WiFi.localIP());

  server.begin();
  Serial.println("Servidor TCP iniciado");
}

// ================================================================
// 🔁 LOOP PRINCIPAL
// ================================================================
void loop() {
  actualizarGesto();

  WiFiClient client = server.available();

  if (client) {
    Serial.println("💻 Cliente conectado");

    while (client.connected()) {
      actualizarGesto();

      if (client.available()) {
        String data = client.readStringUntil('\n');
        data.trim();
        if (data.length() == 0) continue;

        Serial.print("📩 Recibido: ");
        Serial.println(data);

        // ------------------- GESTOS A Y B -------------------------
        if (data == "A,A") {
          ejecutarGesto('A');
          continue;
        }
        if (data == "B,B") {
          ejecutarGesto('B');
          continue;
        }

        // ------------------- GESTOS R#,L# -------------------------
        int commaIndex = data.indexOf(',');
        if (commaIndex == -1) {
          client.println("Formato inválido");
          continue;
        }

        String rightCmd = data.substring(0, commaIndex);
        String leftCmd  = data.substring(commaIndex + 1);

        if (!rightCmd.startsWith("R")) rightCmd = "R" + rightCmd;
        if (!leftCmd.startsWith("L")) leftCmd = "L" + leftCmd;

        // -------- BRAZO IZQUIERDO --------
        if (leftCmd.startsWith("L")) {
          int gestureL = leftCmd.substring(1).toInt();
          switch (gestureL) {
            case 1: moverBrazoIzquierdo(30, 150); break; 
            case 2: moverBrazoIzquierdo(0, 0); break;
            case 3: moverBrazoIzquierdo(100, 80); break; 
            case 4: moverBrazoIzquierdo(0, 180); break;
            case 5: moverBrazoIzquierdo(180, 180); break;
          }
        }

        // -------- BRAZO DERECHO --------
        if (rightCmd.startsWith("R")) {
          int gestureR = rightCmd.substring(1).toInt();
          switch (gestureR) {
            case 1: moverBrazoDerecho(130, 90); break;
            case 2: moverBrazoDerecho(180, 180); break;
            case 3: moverBrazoDerecho(180, 0); break;
            case 4: moverBrazoDerecho(70, 140); break;
            case 5: moverBrazoDerecho(0, 0); break;
          }
        }
      }
    }

    client.stop();
    Serial.println("❌ Cliente desconectado");
  }
}
