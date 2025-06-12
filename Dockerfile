# /home/siisi/atmp/Dockerfile

# 1. Base image
FROM python:3.12.0

# 2. Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

ARG ENVIRONMENT
ENV ENVIRONMENT=${ENVIRONMENT}

# 3. Create work directory
WORKDIR /app

# 4. Install system dependencies

# 5. Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

RUN mkdir -p /app/staticfiles

# 6. Copy project code
COPY . .

# 7. Entrypoint script
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# 8. Use entrypoint script to run migrations, collectstatic and gunicorn
ENTRYPOINT ["/app/entrypoint.sh"]
