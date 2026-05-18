# ESP32 Telemetry & Video Stream System

A comprehensive IoT system built with ESP32 microcontrollers and NRF24L01 radio modules. The system collects environmental data, transmits it wirelessly, hosts a live video stream, and displays the data on an LCD screen. A dedicated PC application for data visualization is currently in development.

## Project Structure

This repository is organized as a monorepo containing three main components:

*   **`src/transmitter/` (Transmitter Node)**
    *   **Hardware:** ESP32-Wrover-E, BME280, NRF24L01, OV2640 Camera.
    *   **Functionality:** Reads temperature, humidity, and pressure from the BME280 sensor, sends the data via NRF24L01 radio, and hosts an HTTP server for M-JPEG video streaming.
*   **`src/receiver/` (Receiver Node)**
    *   **Hardware:** ESP32, NRF24L01, 16x2 I2C LCD Display.
    *   **Functionality:** Listens for incoming radio packets and displays the real-time environmental data on the LCD screen.
*   **`python_gui/` (PC Application)**
    *   **Functionality:** A Python-based desktop application (work in progress) designed to receive the video stream and visualize the telemetry data.

## Technologies & Libraries

*   **PlatformIO / C++** (Firmware development)
*   **RF24** (2.4GHz Radio Communication)
*   **Adafruit BME280** (Environmental sensing)
*   **LiquidCrystal_I2C** (Display control)
*   **ESP32 Camera Driver** (Video streaming)
