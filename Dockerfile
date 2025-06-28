# Dockerfile

# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
# This happens in a clean, isolated environment.
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's source code into the container
COPY . .

# Define the command to run your app
CMD ["python", "-m", "src.stock_advisor_app_001.main"]