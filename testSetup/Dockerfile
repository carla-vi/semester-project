FROM python:3.10-slim

WORKDIR /app

# Copy only the scripts you need
COPY populateEggPrice.py populateEggPrice.py
COPY populateEmails.py populateEmails.py

# Install dependencies
RUN pip install --no-cache-dir pymongo