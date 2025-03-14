#!/bin/bash
apt update && apt install -y poppler-utils tesseract-ocr

pip install -r requirements.txt  # Install Python dependencies
