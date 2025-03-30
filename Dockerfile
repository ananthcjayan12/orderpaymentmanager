# Use the official Python slim image
FROM python:3.10-slim

# Prevent Python buffering (ensures logs stream in real time)
ENV PYTHONUNBUFFERED=1

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies necessary for your packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy the dependency list and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the entire project into the container
COPY . .

# Collect static files (adjust the command if your project uses a different setup)
RUN python manage.py collectstatic --noinput

# Expose port 8000
EXPOSE 8000

# Copy the entrypoint script into the container and make it executable
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh && ls -l /app/entrypoint.sh

# Run the entrypoint, which applies migrations then starts Gunicorn
CMD ["/app/entrypoint.sh"] 