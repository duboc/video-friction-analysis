# Use Python slim image for smaller size while maintaining functionality
FROM python:3.9-slim

# Set environment variables
ENV PYTHONUNBUFFERED True
ENV PORT 8080

# Install system dependencies including libmagic
RUN apt-get update -y && apt-get install -y \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Create and set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy local code to the container image
COPY . .

# Create directory for prompts if it doesn't exist
RUN mkdir -p prompts

# Set Streamlit specific config
RUN mkdir -p /root/.streamlit
RUN echo "\
[server]\n\
port = ${PORT}\n\
address = 0.0.0.0\n\
enableXsrfProtection = false\n\
enableCORS = false\n\
\n\
[browser]\n\
serverAddress = 0.0.0.0\n\
serverPort = ${PORT}\n\
" > /root/.streamlit/config.toml

# Expose port
EXPOSE ${PORT}

# Run Streamlit
CMD streamlit run app.py --server.port=${PORT}