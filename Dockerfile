# Start with a modern Python version
FROM python:3.9-slim

# Set environment variables for security and performance
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /app

# Install dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project files
COPY . /app/

# Collect static files into the /app/staticfiles/ directory
RUN python manage.py collectstatic --no-input

# Expose the port Gunicorn will run on
EXPOSE 8000