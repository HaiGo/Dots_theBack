# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory
WORKDIR /app

# Copy the dependencies file to the working directory
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the content of the local src directory to the working directory
COPY . .

# Expose port 8080
EXPOSE 8080

# Set environment variables for Gunicorn
ENV MODULE_NAME="run:app"
ENV VARIABLE_NAME="app"

# Run the web service on container startup
# Note: Migrations should be run manually via Railway CLI when needed
# Using fixed port 8080, Railway will handle external port mapping
CMD ["gunicorn", "run:app", "--workers=4", "--bind=0.0.0.0:8080", "--timeout=120", "--log-level=info"]

