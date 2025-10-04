# Use the official Python image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /code

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the port the app runs on
EXPOSE 7860

# Command to run the application using gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:7860", "app:app"]