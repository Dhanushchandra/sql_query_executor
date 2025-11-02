FROM python:3.11-slim

WORKDIR /app

# Copy dependency file and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Environment variables
ENV DATABASE_PATH=sql_runner.db
ENV JWT_SECRET=super_secret_key
ENV JWT_ALGORITHM=HS256
ENV JWT_EXP_MINUTES=60
ENV FLASK_ENV=production

# Expose backend port
EXPOSE 5000

# Run database setup before Flask
CMD ["sh", "-c", "python setup_db.py && python app.py"]
