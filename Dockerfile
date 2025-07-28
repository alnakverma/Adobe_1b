# d:\Placement\RESUME\GitHub\Adobe_Hackathon\Dockerfile

# Use a slim Python base image compatible with AMD64
FROM --platform=linux/amd64 python:3.9-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file first to leverage Docker cache
COPY src/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code and models
COPY src/ .
COPY models/ ./models/
COPY input/ ./input/

# This command will be executed when the container starts
# Running as a module is best practice
CMD ["python", "-m", "main"]