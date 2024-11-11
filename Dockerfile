FROM python:3.12

# Set working directory
WORKDIR /app

# Copy project files
COPY . .

# Install system dependencies including libmagic
RUN apt-get update -y && apt-get install -y \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

ENV GCP_PROJECT=yourprojectid
ENV GCS_BUCKET=yourbucketname

EXPOSE 8080

# Run Streamlit app
CMD ["streamlit", "run", "app.py", "--server.port=8080"]