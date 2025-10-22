# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code into the container
COPY src/ /app/src

# Set environment variables for the application
ENV APP_HOST=0.0.0.0
ENV APP_PORT=8000
ENV ROOT_PATH=""

# Run the application with ROOT_PATH set for load balancer compatibility
CMD uvicorn src.main:app --host $APP_HOST --port $APP_PORT
