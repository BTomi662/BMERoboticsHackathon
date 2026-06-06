#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

// Initialize the PCA9685 driver using the default I2C address (0x40)
Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver();

// PCA9685 Servo Pulse Settings (Standard 50Hz Servo)
#define SERVOMIN   150  // 0 degrees
#define SERVOMAX   600  // 180 degrees
#define SERVO_HALF 375  // 90 degrees

// Define which channel on the PCA9685 the servo is plugged into (0 to 15)
const int SERVO_CHANNEL = 0; 

// Custom I2C pins for ESP32-S3
const int I2C_SDA = 19;
const int I2C_SCL = 21;

// --- MOTOR A PINS ---
#define MOTOR_A_PWM  4  // Speed Control (PWMA)
#define MOTOR_A_DIR1 5  // Direction Pin 1 (AIN1)
#define MOTOR_A_DIR2 10 // New Direction Pin 2 (AIN2) - Adjust GPIO if needed

// --- MOTOR B PINS ---
#define MOTOR_B_PWM  7  // Speed Control (PWMB)
#define MOTOR_B_DIR1 6  // Direction Pin 1 (BIN1)
#define MOTOR_B_DIR2 11 // New Direction Pin 2 (BIN2) - Adjust GPIO if needed

// TB6612 Standby Pin
#define STBY_PIN 8

#define TOUCH_SENSOR_PIN 39

// Define Speed (0 to 255)
#define MOTOR_SPEED 200

// --- COORDINATE NAVIGATION VARIABLES ---
float currentX = 0.0;
float currentY = 0.0;
const float UNITS_PER_MS = 0.005;

void setup() {
  Serial.begin(115200);
  delay(1000);

  // Initialize I2C with specific ESP32-S3 pins
  Wire.begin(I2C_SDA, I2C_SCL);

  // Initialize the PCA9685
  pwm.begin();
  pwm.setOscillatorFrequency(27000000);
  pwm.setPWMFreq(50);  

  Serial.println("PCA9685 Servo Controller Initialized.");
  delay(10);

  // Configure the Standby pin
  pinMode(STBY_PIN, OUTPUT);
  digitalWrite(STBY_PIN, HIGH); 

  // Configure Motor Direction and PWM pins as outputs
  pinMode(MOTOR_A_PWM, OUTPUT);
  pinMode(MOTOR_A_DIR1, OUTPUT);
  pinMode(MOTOR_A_DIR2, OUTPUT);
  
  pinMode(MOTOR_B_PWM, OUTPUT);
  pinMode(MOTOR_B_DIR1, OUTPUT);
  pinMode(MOTOR_B_DIR2, OUTPUT);

  // Set the PWM frequency to 5kHz to eliminate motor whining noise
  analogWriteFrequency(MOTOR_A_PWM, 5000); 
  analogWriteFrequency(MOTOR_B_PWM, 5000); 

  Serial.println("TB6612 Motor Driver Initialized (6-Pin Mode).");

  pinMode(TOUCH_SENSOR_PIN, INPUT_PULLDOWN);
}

void loop() {
  if (digitalRead(TOUCH_SENSOR_PIN) == HIGH) {
    Serial.println("Moving Up...");
    moveUp(MOTOR_SPEED);
    delay(2000);

    Serial.println("Moving Down...");
    moveDown(MOTOR_SPEED);
    delay(2000);

    Serial.println("Moving Left (Both Clockwise)...");
    moveLeft(MOTOR_SPEED);
    delay(2000);

    Serial.println("Moving Right (Both Anti-Clockwise)...");
    moveRight(MOTOR_SPEED);
    delay(2000);

    Serial.println("Stopping...");
    stopMotors();
    delay(3000); 

    Serial.println("Raising Magnet...");
    magnetUp();
    delay(3000); 

    Serial.println("Lowering Magnet...");
    magnetDown();
    delay(3000); 

    // Move to coordinate (10, 15)
    Serial.println("--- Navigating to (10, 15) ---");
    moveToCoordinate(10.0, 15.0);
    delay(5000);

    // Move back to coordinate (0, 0)
    Serial.println("--- Navigating to (0, 0) ---");
    moveToCoordinate(0.0, 0.0);
    delay(5000);
  }
  delay(10);
}

// --- MOVEMENT FUNCTIONS ---

// moveUp: Motors spin in opposite directions
void moveUp(int speed) {
  // Motor A Clockwise
  digitalWrite(MOTOR_A_DIR1, HIGH);
  digitalWrite(MOTOR_A_DIR2, LOW);
  analogWrite(MOTOR_A_PWM, speed); 

  // Motor B Anti-Clockwise
  digitalWrite(MOTOR_B_DIR1, LOW);
  digitalWrite(MOTOR_B_DIR2, HIGH);
  analogWrite(MOTOR_B_PWM, speed); 
}

// moveDown: Motors spin in opposite directions (reversed from moveUp)
void moveDown(int speed) {
  // Motor A Anti-Clockwise
  digitalWrite(MOTOR_A_DIR1, LOW);
  digitalWrite(MOTOR_A_DIR2, HIGH);
  analogWrite(MOTOR_A_PWM, speed);

  // Motor B Clockwise
  digitalWrite(MOTOR_B_DIR1, HIGH);
  digitalWrite(MOTOR_B_DIR2, LOW);
  analogWrite(MOTOR_B_PWM, speed);
}

// moveLeft: Both motors spin Clockwise
void moveLeft(int speed) {
  digitalWrite(MOTOR_A_DIR1, HIGH);
  digitalWrite(MOTOR_A_DIR2, LOW);
  analogWrite(MOTOR_A_PWM, speed);

  digitalWrite(MOTOR_B_DIR1, HIGH);
  digitalWrite(MOTOR_B_DIR2, LOW);
  analogWrite(MOTOR_B_PWM, speed);
}

// moveRight: Both motors spin Anti-Clockwise
void moveRight(int speed) {
  digitalWrite(MOTOR_A_DIR1, LOW);
  digitalWrite(MOTOR_A_DIR2, HIGH);
  analogWrite(MOTOR_A_PWM, speed);

  digitalWrite(MOTOR_B_DIR1, LOW);
  digitalWrite(MOTOR_B_DIR2, HIGH);
  analogWrite(MOTOR_B_PWM, speed);
}

// Helper function to stop the motors completely
void stopMotors() {
  digitalWrite(MOTOR_A_DIR1, LOW);
  digitalWrite(MOTOR_A_DIR2, LOW);
  digitalWrite(MOTOR_B_DIR1, LOW);
  digitalWrite(MOTOR_B_DIR2, LOW);
  analogWrite(MOTOR_A_PWM, 0);
  analogWrite(MOTOR_B_PWM, 0);
}

// magnetUp: Moves the servo to 0 degrees
void magnetUp() {
  pwm.setPWM(SERVO_CHANNEL, 0, SERVOMIN); 
}

// magnetDown: Moves the servo to 90 degrees
void magnetDown() {
  pwm.setPWM(SERVO_CHANNEL, 0, SERVO_HALF);
}

// Coordinate tracking navigation (Top-Left Origin)
void moveToCoordinate(float targetX, float targetY) {
  float deltaX = targetX - currentX;
  float deltaY = targetY - currentY;

  Serial.print("Current Pos: ("); Serial.print(currentX); Serial.print(", "); Serial.print(currentY); Serial.println(")");
  Serial.print("Target Pos: ("); Serial.print(targetX); Serial.print(", "); Serial.print(targetY); Serial.println(")");

  // 1. Handle X-Axis Movements (Left / Right)
  if (deltaX != 0) {
    unsigned long durationX = abs(deltaX) / UNITS_PER_MS;

    if (deltaX > 0) {
      Serial.print("Moving Right (Increasing X) for "); Serial.print(durationX); Serial.println(" ms");
      moveRight(MOTOR_SPEED);
    } else {
      Serial.print("Moving Left (Decreasing X) for "); Serial.print(durationX); Serial.println(" ms");
      moveLeft(MOTOR_SPEED);
    }
    delay(durationX);
    stopMotors();
    currentX = targetX; 
  }

  // 2. Handle Y-Axis Movements (Up / Down)
  if (deltaY != 0) {
    unsigned long durationY = abs(deltaY) / UNITS_PER_MS;

    if (deltaY > 0) {
      Serial.print("Moving Down (Increasing Y) for "); Serial.print(durationY); Serial.println(" ms");
      moveDown(MOTOR_SPEED);
    } else {
      Serial.print("Moving Up (Decreasing Y) for "); Serial.print(durationY); Serial.println(" ms");
      moveUp(MOTOR_SPEED);
    }
    delay(durationY);
    stopMotors();
    currentY = targetY; 
  }

  Serial.println("Target Destination Reached.");
  Serial.println("--------------------------------");
}