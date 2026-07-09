FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install system dependencies, git, curl, gcc (for compiling psutil if needed), and docker CLI
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    gcc \
    python3-dev \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Docker CLI client (to allow Docker CLI commands inside the container)
RUN curl -fsSL https://download.docker.com/linux/static/stable/x86_64/docker-24.0.9.tgz -o /tmp/docker.tgz \
    && tar -xzf /tmp/docker.tgz -C /tmp \
    && mv /tmp/docker/docker /usr/local/bin/docker \
    && rm -rf /tmp/docker*

# Set working directory
WORKDIR /app

# Copy requirements and install python packages (including pytest, flake8, and psutil)
COPY requirements.txt /app/requirements.txt
RUN pip3 install --no-cache-dir -r requirements.txt

# Install Ansible via pip
RUN pip3 install --no-cache-dir ansible

# Install community.docker collection for Ansible container remediation
RUN ansible-galaxy collection install community.docker

# Copy scripts and tests
COPY scripts/ /app/scripts/
COPY tests/ /app/tests/

# Default runtime command
CMD ["python3", "scripts/health_engine.py"]
