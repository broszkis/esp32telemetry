#include "esp_camera.h"
#include <WiFi.h>
#include "esp_http_server.h"
#include <Wire.h>
#include <SPI.h>

#define sensor_t adafruit_sensor_t
#include <Adafruit_Sensor.h>
#include <Adafruit_BME280.h>
#undef sensor_t

#include <RF24.h>

//Network Configuration
const char* WIFI_SSID = "ssid";
const char* WIFI_PASS = "password";

//Camera Pins (ESP32-WROVER-KIT)
constexpr int CAM_PIN_PWDN   = -1;
constexpr int CAM_PIN_RESET  = -1;
constexpr int CAM_PIN_XCLK   = 21;
constexpr int CAM_PIN_SIOD   = 26;
constexpr int CAM_PIN_SIOC   = 27;
constexpr int CAM_PIN_D7     = 35;
constexpr int CAM_PIN_D6     = 34;
constexpr int CAM_PIN_D5     = 39;
constexpr int CAM_PIN_D4     = 36;
constexpr int CAM_PIN_D3     = 19;
constexpr int CAM_PIN_D2     = 18;
constexpr int CAM_PIN_D1     = 5;
constexpr int CAM_PIN_D0     = 4;
constexpr int CAM_PIN_VSYNC  = 25;
constexpr int CAM_PIN_HREF   = 23;
constexpr int CAM_PIN_PCLK   = 22;

//BME280 Pins
constexpr uint8_t PIN_I2C_SDA = 32;
constexpr uint8_t PIN_I2C_SCL = 33;
Adafruit_BME280 bme; 

//NRF24L01 Pins
constexpr uint8_t PIN_NRF_CE   = 2;
constexpr uint8_t PIN_NRF_CSN  = 15;
constexpr uint8_t PIN_SPI_SCK  = 14;
constexpr uint8_t PIN_SPI_MISO = 12;
constexpr uint8_t PIN_SPI_MOSI = 13;
RF24 radio(PIN_NRF_CE, PIN_NRF_CSN);

const uint64_t NRF_ADDRESS = 0xF0F0F0F0E1LL;

//Data Structure
struct __attribute__((packed)) DataPacket {
    float temp;
    float humi;
    float pressure;
    uint32_t counter;
};
DataPacket data;

httpd_handle_t stream_httpd = NULL;

//Camera Stream Handler
static esp_err_t stream_handler(httpd_req_t *req) {
    camera_fb_t * fb = NULL;
    esp_err_t res = ESP_OK;
    char part_buf[64];

    res = httpd_resp_set_type(req, "multipart/x-mixed-replace;boundary=frame");
    if (res != ESP_OK) return res;

    while (true) {
        fb = esp_camera_fb_get();
        if (!fb) {
            res = ESP_FAIL;
        } else {
            size_t hlen = snprintf(part_buf, 64, "\r\n--frame\r\nContent-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n", fb->len);
            res = httpd_resp_send_chunk(req, (const char *)part_buf, hlen);
            if (res == ESP_OK) {
                res = httpd_resp_send_chunk(req, (const char *)fb->buf, fb->len);
            }
            esp_camera_fb_return(fb);
        }
        if (res != ESP_OK) break;
    }
    return res;
}

//Initialization Functions
void initCamera() {
    camera_config_t config;
    config.ledc_channel = LEDC_CHANNEL_0;
    config.ledc_timer   = LEDC_TIMER_0;
    config.pin_d0       = CAM_PIN_D0;
    config.pin_d1       = CAM_PIN_D1;
    config.pin_d2       = CAM_PIN_D2;
    config.pin_d3       = CAM_PIN_D3;
    config.pin_d4       = CAM_PIN_D4;
    config.pin_d5       = CAM_PIN_D5;
    config.pin_d6       = CAM_PIN_D6;
    config.pin_d7       = CAM_PIN_D7;
    config.pin_xclk     = CAM_PIN_XCLK;
    config.pin_pclk     = CAM_PIN_PCLK;
    config.pin_vsync    = CAM_PIN_VSYNC;
    config.pin_href     = CAM_PIN_HREF;
    config.pin_sccb_sda = CAM_PIN_SIOD;
    config.pin_sccb_scl = CAM_PIN_SIOC;
    config.pin_pwdn     = CAM_PIN_PWDN;
    config.pin_reset    = CAM_PIN_RESET;
    
    config.xclk_freq_hz = 20000000;
    config.pixel_format = PIXFORMAT_JPEG;
    config.frame_size   = FRAMESIZE_VGA;
    config.jpeg_quality = 12;
    config.fb_count     = 1;

    if (esp_camera_init(&config) != ESP_OK) {
        Serial.println("Camera initalization error");
    } else {
        Serial.println("Camera ready");
    }
}

void startCameraServer() {
    httpd_config_t server_config = HTTPD_DEFAULT_CONFIG();
    server_config.server_port = 80;
    httpd_uri_t stream_uri = { .uri = "/", .method = HTTP_GET, .handler = stream_handler, .user_ctx = NULL };
    
    if (httpd_start(&stream_httpd, &server_config) == ESP_OK) {
        httpd_register_uri_handler(stream_httpd, &stream_uri);
        Serial.println("HTTP streaming server started");
    }
}

void setup() {
    Serial.begin(115200);
    data.counter = 0;
    
    //I2C & BME280 Setup
    Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL);
    if (!bme.begin(0x76, &Wire)) {
        Serial.println("Module BME280 not found");
    }

    //SPI & NRF24L01 Setup
    SPI.begin(PIN_SPI_SCK, PIN_SPI_MISO, PIN_SPI_MOSI, PIN_NRF_CSN);
    if (!radio.begin(&SPI)) {
        Serial.println("Module NRF24L01 not found");
    } else {
        radio.setPALevel(RF24_PA_LOW);    
        radio.setDataRate(RF24_2MBPS);    
        radio.setChannel(76);             
        radio.setRetries(15, 15);         
        radio.openWritingPipe(NRF_ADDRESS);
        radio.stopListening();
        Serial.println("Transmitter NRF24L01 ready");
    }

    //Camera Setup
    initCamera();

    //WiFi Setup
    WiFi.begin(WIFI_SSID, WIFI_PASS);
    Serial.print("Connecting to WiFi...");
    while (WiFi.status() != WL_CONNECTED) { 
        delay(500); 
        Serial.print("."); 
    }
    Serial.println("\nConnected to WiFi");

    //Server Setup
    startCameraServer();
}

void loop() {
    data.temp = bme.readTemperature();
    data.humi = bme.readHumidity();
    
    data.pressure = bme.readPressure() / 100.0F; 
    data.counter++;

    bool report = radio.write(&data, sizeof(DataPacket));
    
    if (report) {
        Serial.printf("Sent packet: %u | Temp: %.2f | Humidity: %.2f | Pressure: %.2f hPa\n", 
                      data.counter, data.temp, data.humi, data.pressure);
    } else {
        Serial.println("Transmission error (No ACK from receiver)");
    }

    delay(2000); 
}