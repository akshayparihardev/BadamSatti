# Dockerfile

# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project files into the container
COPY . /app/

# Collect static files for production
RUN python manage.py collectstatic --no-input

# Expose the port Gunicorn will run on
EXPOSE 8000

# Run the Gunicorn server
# Make sure 'project.wsgi' matches your project folder name
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "project.wsgi:application"]