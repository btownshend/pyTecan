int sensorPin = A0;    // select the input pin for the potentiometer

void setup() {
  Serial.begin(9600);
}

void loop() {
  if (Serial.available() > 0) {
    int inByte = Serial.read();
    // read the value from the sensor:
    int sensorValue = analogRead(sensorPin);
    Serial.write(sensorValue/256);
    Serial.write(sensorValue%256);
  }
}
