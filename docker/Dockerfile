FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Set workdir
WORKDIR /app

# Copy Python dependencies
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy entire application
COPY . .

# Set environment variable for Streamlit
ENV STREAMLIT_SERVER_PORT=8501

# Expose port
EXPOSE 8501

# Start the app
CMD ["streamlit", "run", "genai_dashboard.py", "--server.port=8501", "--server.address=0.0.0.0"]

