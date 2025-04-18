#!/bin/bash

# Update package lists
echo "Updating package lists..."
sudo apt update

# Install required system dependencies
echo "Installing system dependencies..."
sudo apt install -y wget curl unzip

# Install Chrome
echo "Installing Chrome..."
wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo apt install -y ./google-chrome-stable_current_amd64.deb
rm google-chrome-stable_current_amd64.deb

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Verify Chrome installation
echo "Verifying Chrome installation..."
google-chrome --version

echo "Setup complete! You can now run the scraper using: python Scrapper.py" 