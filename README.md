# ESP32 Telemetry & Video Stream System

A comprehensive IoT ecosystem built with ESP32 microcontrollers and NRF24L01 radio modules. This system seamlessly integrates environmental data collection, wireless RF transmission, and live M-JPEG video streaming into a single, cohesive project.

## Key Features

* **Real-Time Telemetry:** Continuous monitoring of temperature, humidity, and barometric pressure.
* **Wireless Communication:** Robust 2.4GHz RF transmission between nodes using NRF24L01 modules.
* **Live Video Feed:** Embedded HTTP server hosting an M-JPEG stream directly from the microcontroller.
* **Instant Feedback:** Localized data visualization on an I2C LCD screen.
* **PC Integration:** Dedicated Python-based desktop application for advanced data visualization and stream monitoring.

## Hardware Requirements

**Transmitter Node (Sensor & Camera):**
* ESP32-Wrover-E Microcontroller
* BME280 Environmental Sensor
* NRF24L01 RF Transceiver
* OV2640 Camera Module

**Receiver Node (Display):**
* ESP32 Microcontroller (Standard)
* NRF24L01 RF Transceiver
* 16x2 LCD Display (with I2C interface)

## Project Structure

This repository is organized as a PlatformIO monorepo containing three main components.

### `src/transmitter/`
The data collection and streaming hub. It reads environmental metrics from the BME280, broadcasts them via the NRF24L01 module, and simultaneously hosts an HTTP server to broadcast the live video stream from the camera.

### `src/receiver/`
The local monitoring station. It actively listens for incoming RF data packets from the transmitter and immediately displays the real-time environmental metrics on the attached LCD screen.

### `gui/`
The central PC monitoring application built in Python. Key modules include:
* **`main.py` & `gui.py`**: Core application logic and user interface.
* **`workers/`**: Dedicated background threads (e.g., `video_receiver.py`, `serial_receiver.py`, `telemetry_logger.py`) ensuring smooth UI performance during data acquisition.
* **`config.py` & `telemetry_utils.py`**: Configuration parameters and helper functions.

## Technologies & Libraries

**Firmware (C++ / PlatformIO)**
* `RF24` - 2.4GHz Radio Communication
* `Adafruit BME280` - Environmental Sensing
* `LiquidCrystal_I2C` - Display Control
* `esp32-camera` - Video Streaming Driver
