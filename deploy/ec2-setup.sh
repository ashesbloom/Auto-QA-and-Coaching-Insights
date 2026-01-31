#!/bin/bash
# EC2 User Data Script for Battery Smart Auto-QA System
# Run this script on a fresh Ubuntu 22.04 EC2 instance

set -e

echo "=== Battery Smart Auto-QA System Setup ==="

# Update system
apt-get update
apt-get upgrade -y

# Install Docker
echo "Installing Docker..."
apt-get install -y ca-certificates curl gnupg
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Start Docker
systemctl start docker
systemctl enable docker

# Add ubuntu user to docker group
usermod -aG docker ubuntu

# Install AWS CLI
echo "Installing AWS CLI..."
apt-get install -y awscli

# Create application directory
mkdir -p /opt/battery-smart
cd /opt/battery-smart

# Clone repository (replace with your repo URL)
echo "Cloning repository..."
# git clone https://github.com/ashesbloom/Auto-QA-and-Coaching-Insights.git .

# Create .env file from EC2 instance metadata or SSM Parameter Store
echo "Creating environment configuration..."
cat > .env << 'EOF'
# AWS Configuration
USE_AWS=true
AWS_REGION=us-east-1

# Bedrock LLM
AWS_BEDROCK_MODEL=anthropic.claude-3-haiku-20240307-v1:0
AWS_BEDROCK_STREAMING=true

# Polly TTS
AWS_POLLY_VOICE=Kajal
AWS_POLLY_ENGINE=neural

# S3 Storage (replace with your bucket)
AWS_S3_BUCKET=battery-smart-transcripts

# Flask
FLASK_SECRET_KEY=your-secret-key-here
DEBUG=false
EOF

# Build and run with Docker Compose
echo "Building and starting application..."
cd deploy
docker compose up -d --build

echo "=== Setup Complete ==="
echo "Application is running on port 5000"
echo "Access the dashboard at: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):5000"
