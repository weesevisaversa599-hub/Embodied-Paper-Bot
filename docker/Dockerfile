FROM python:3.11-slim

WORKDIR /app

# Install dependencies directly in the container
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Run the scheduler
CMD ["python", "run.py"]
