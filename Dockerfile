FROM python:3.12-slim-bookworm

# Install curl, Node.js, git, and other dependencies
RUN apt-get update && \
    apt-get install -y curl ca-certificates git tesseract-ocr ffmpeg && \
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs && \
    npm install -g prettier@3.4.2 && \
    rm -rf /var/lib/apt/lists/*

# Configure git
RUN git config --global user.name "21f3001076" && \
    git config --global user.email "21f3001076@ds.study.iitm.ac.in"

# Download and install uv
ADD https://astral.sh/uv/install.sh /uv-installer.sh
RUN sh /uv-installer.sh && rm /uv-installer.sh

# Ensure the installed binary is on the `PATH`
ENV PATH="/root/.local/bin/:$PATH"

# Set the working directory
WORKDIR /app

# Copy the current directory contents into the container
COPY . /app

# Upgrade pip
RUN pip install --upgrade pip

# Install any needed packages
RUN pip install --no-cache-dir --root-user-action=ignore -r requirements.txt

# Expose port 8000
EXPOSE 8000

# Set environment variables (AIPROXY_TOKEN needs to be set at runtime)
ENV PYTHONUNBUFFERED=1

# Run the application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]