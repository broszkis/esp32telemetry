#include <SPI.h>
#include <RF24.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

//Configuration & Pins
constexpr uint8_t PIN_NRF_CE   = 16;
constexpr uint8_t PIN_NRF_CSN  = 15;
constexpr uint8_t PIN_SPI_SCK  = 14;
constexpr uint8_t PIN_SPI_MOSI = 13;
constexpr uint8_t PIN_SPI_MISO = 12;

constexpr uint8_t PIN_I2C_SDA  = 0;
constexpr uint8_t PIN_I2C_SCL  = 2;

const uint64_t NRF_ADDRESS = 0xF0F0F0F0E1LL;

//Data Structures
struct __attribute__((packed)) DataPacket {
    float temp;
    float humi;
    float pressure; 
    uint32_t counter;
};
DataPacket data;

//Globals
SPIClass hspi(HSPI);
RF24 radio(PIN_NRF_CE, PIN_NRF_CSN);
LiquidCrystal_I2C lcd(0x27, 16, 2);

void setup() {
    Serial.begin(115200);
    delay(1000);
    Serial.println("\nRECEIVER NODE START");

    //I2C & LCD Init
    Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL);
    lcd.init();
    lcd.backlight();
    lcd.setCursor(0, 0);
    lcd.print("Waiting for data...");

    //SPI & NRF24 Init
    hspi.begin(PIN_SPI_SCK, PIN_SPI_MISO, PIN_SPI_MOSI, PIN_NRF_CSN);
    if (radio.begin(&hspi)) {
        radio.setPALevel(RF24_PA_LOW);
        radio.setDataRate(RF24_2MBPS);
        radio.setChannel(76);
        radio.openReadingPipe(1, NRF_ADDRESS);
        radio.startListening();
        Serial.println("Radio ready, listening...");
    } else {
        Serial.println("ERROR: Radio not responding...");
        lcd.setCursor(0, 1);
        lcd.print("No NRF radio found...");
    }
}

void loop() {
    if (radio.available()) {
        radio.read(&data, sizeof(DataPacket));

        Serial.printf("Received! #%u | Temp: %.2f | Humidity: %.2f | Pressure: %.2f hPa\n", 
                      data.counter, data.temp, data.humi, data.pressure);
        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.print("T:"); lcd.print(data.temp, 1); lcd.print("C");
        lcd.setCursor(9, 0);
        lcd.print("H:"); lcd.print(data.humi, 0); lcd.print("%");
        
        lcd.setCursor(0, 1);
        lcd.print("P:"); lcd.print(data.pressure, 0); lcd.print("hPa");
        lcd.setCursor(11, 1);
        lcd.print("#"); lcd.print(data.counter);
    }
}