# Intellicart Setup Guide (Raspberry Pi)

This guide provides step-by-step instructions to install and run the Intellicart project on a Raspberry Pi.

## System Update & Dependencies

```bash
sudo apt update -y
sudo apt upgrade -y
sudo apt install git python3-pip python3-setuptools python3-smbus -y
````

## Clone the Repository

```bash
cd ~/
git clone -b project https://github.com/rushiranpise/car.git --depth 1
cd car
```

## Install Component Libraries

### Sensor-HAT

```bash
cd sensor-hat
sudo python3 install.py
cd ..
```

### Video Library

```bash
cd videolib
sudo python3 install.py
cd ..
```

### Intellicart Core

```bash
cd intellicart
sudo pip3 install . --break
cd ..
```

### Controller Module

```bash
cd controller
sudo python3 setup.py install
cd ..
```

### Sensor-HAT

```bash
cd sendorhat
sudo bash i2samp.sh
cd ..
```

## Raspberry Pi Configuration

```bash
sudo raspi-config
```

Enable I2C, SPI, Camera, and other required interfaces.

## Run the Application

```bash
sudo python3 app.py
