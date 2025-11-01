#!/bin/bash

# VibeVoice API Server Setup Script
# This script helps set up the VibeVoice API server

set -e  # Exit on error

echo "======================================"
echo "VibeVoice API Server Setup"
echo "======================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${YELLOW}ℹ${NC} $1"
}

# Check if Docker is installed
check_docker() {
    if command -v docker &> /dev/null; then
        print_success "Docker is installed"
        docker --version
        return 0
    else
        print_error "Docker is not installed"
        echo "Please install Docker from https://docs.docker.com/get-docker/"
        return 1
    fi
}

# Check if Docker Compose is installed
check_docker_compose() {
    if command -v docker-compose &> /dev/null || docker compose version &> /dev/null; then
        print_success "Docker Compose is installed"
        docker-compose --version 2>/dev/null || docker compose version
        return 0
    else
        print_error "Docker Compose is not installed"
        echo "Please install Docker Compose from https://docs.docker.com/compose/install/"
        return 1
    fi
}

# Check if NVIDIA Docker is available (for GPU support)
check_nvidia_docker() {
    if docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi &> /dev/null; then
        print_success "NVIDIA Docker is available"
        return 0
    else
        print_info "NVIDIA Docker not available (GPU support disabled)"
        return 1
    fi
}

# Create necessary directories
create_directories() {
    print_info "Creating directories..."
    mkdir -p models/vibevoice
    mkdir -p output
    mkdir -p loras
    print_success "Directories created"
}

# Create .env file from example
create_env_file() {
    if [ ! -f .env ]; then
        print_info "Creating .env file from .env.example..."
        cp .env.example .env
        print_success ".env file created"
        print_info "You can edit .env to customize configuration"
    else
        print_info ".env file already exists"
    fi
}

# Download a model
download_model() {
    local model_name=$1
    local model_dir="models/vibevoice/$model_name"

    if [ -d "$model_dir" ]; then
        print_info "Model $model_name already exists"
        return 0
    fi

    print_info "Downloading $model_name from HuggingFace..."
    print_info "This may take several minutes depending on your connection..."

    if command -v git &> /dev/null; then
        cd models/vibevoice
        git clone "https://huggingface.co/microsoft/$model_name"
        cd ../..
        print_success "Model $model_name downloaded"
    else
        print_error "git is not installed. Please install git to download models."
        return 1
    fi
}

# Main setup flow
main() {
    echo "Step 1: Checking prerequisites..."
    echo ""

    # Check Docker
    if ! check_docker; then
        exit 1
    fi

    # Check Docker Compose
    if ! check_docker_compose; then
        exit 1
    fi

    # Check NVIDIA Docker (optional)
    check_nvidia_docker

    echo ""
    echo "Step 2: Setting up project..."
    echo ""

    # Create directories
    create_directories

    # Create .env file
    create_env_file

    echo ""
    echo "Step 3: Downloading models..."
    echo ""

    # Ask user which model to download
    echo "Which model would you like to download?"
    echo "1) VibeVoice-1.5B (5.4GB, fast, recommended for testing)"
    echo "2) VibeVoice-Large (18.7GB, best quality)"
    echo "3) VibeVoice-Large-Q8 (11.6GB, quantized)"
    echo "4) Skip model download (I'll download manually)"
    echo ""
    read -p "Enter your choice (1-4): " model_choice

    case $model_choice in
        1)
            download_model "VibeVoice-1.5B"
            ;;
        2)
            download_model "VibeVoice-Large"
            ;;
        3)
            download_model "VibeVoice-Large-Q8"
            ;;
        4)
            print_info "Skipping model download"
            print_info "Download models manually to models/vibevoice/"
            ;;
        *)
            print_error "Invalid choice"
            exit 1
            ;;
    esac

    echo ""
    echo "======================================"
    echo "Setup Complete!"
    echo "======================================"
    echo ""
    print_success "VibeVoice API Server is ready to use"
    echo ""
    echo "Next steps:"
    echo "1. Start the server: docker-compose up -d"
    echo "2. Check logs: docker-compose logs -f"
    echo "3. Test the API: curl http://localhost:8000/api/health"
    echo "4. View docs: http://localhost:8000/docs"
    echo ""
    echo "For more information, see README.md and QUICKSTART.md"
    echo ""
}

# Run main function
main
