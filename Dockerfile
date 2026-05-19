FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies via poetry or requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create storage directory for results and persistence
RUN mkdir -p /app/storage/results

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Command to run the app using the new module name
CMD ["uvicorn", "genbox.main:app", "--host", "0.0.0.0", "--port", "8000"]
