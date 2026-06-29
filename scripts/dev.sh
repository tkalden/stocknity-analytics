#!/bin/bash

# Stock Portfolio Local Development Script
set -e

echo "🚀 Starting Stock Portfolio local development..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose and try again."
    exit 1
fi

# Stop any existing containers
print_status "Stopping existing containers..."
docker-compose down

# Build and start services
print_status "Building and starting services..."
docker-compose up --build -d

# Wait for services to be ready
print_status "Waiting for services to be ready..."
sleep 10

# Check if Redis is ready
print_status "Checking Redis connection..."
if docker-compose exec redis redis-cli ping | grep -q "PONG"; then
    print_status "Redis is ready! ✅"
else
    print_warning "Redis might not be ready yet. Waiting a bit more..."
    sleep 5
fi

# Check if Flask app is ready
print_status "Checking Flask application..."
if curl -f http://localhost:5001/ > /dev/null 2>&1; then
    print_status "Flask application is ready! ✅"
else
    print_warning "Flask application might not be ready yet. Check logs below."
fi

print_status "Local development environment is running! 🎉"
print_status "Application URL: http://localhost:5001"
print_status "Redis URL: localhost:6379"

print_status "Showing logs (Ctrl+C to stop)..."
docker-compose logs -f 