# DeepAnalyze Docker Environment

A production-ready Docker environment for DeepAnalyze, featuring external API integration for flexible LLM provider support.

## 🚀 Quick Start

### Prerequisites

- Docker installed
- NVIDIA GPU with CUDA support (for GPU acceleration)
- NVIDIA Container Toolkit (for GPU support)

## 📦 Deployment Options

### Option 1: Pull from Docker Hub (Recommended)

The easiest way to get started - pull the pre-built image:

```bash
# Pull the image
docker pull facdbe/deepanalyze-env:latest

# Run with GPU support
docker run --gpus all -it --rm \
  -p 8000:8000 \
  facdbe/deepanalyze-env:latest

```

### Option 2: Build from Dockerfile

Build the image from source for customization:

```bash
# Clone the repository
git clone https://github.com/ruc-datalab/DeepAnalyze.git
cd DeepAnalyze/docker

# Build the image
docker build -t deepanalyze-env:latest .

# Run the container
docker run --gpus all -it --rm \
  -p 8000:8000 \
  deepanalyze-env:latest
```

## 🔧 API Server Deployment

### Start DeepAnalyze API Server

```bash
docker run -d \
  -p 8200:8200 \
  -p 3001:3001 \
  -e DEEPSEEK_API_KEY="your-api-key-here" \
  -e OPENAI_API_KEY="your-openai-key-here" \
  --name deepanalyze-api \
  deepanalyze-env:latest
```

### API Endpoints

Once the API server is running, you can access:

- **API Base**: `http://localhost:8200`
- **LLM Manager API**: `http://localhost:8200/llm-manager/api`
- **Management UI**: `http://localhost:3001`
- **OpenAI-compatible endpoint**: `http://localhost:8200/llm-manager/api/proxy/chat/completions`
- **File upload endpoint**: `http://localhost:8200/llm-manager/api/proxy/files`


## 📦 Image Size

- **Total Size**: ~3GB
- **Base Runtime**: ~1.5GB
- **Python Dependencies**: ~1GB
- **Data Science Tools**: ~0.5GB


## 🤝 Contributing

Issues and pull requests are welcome!

## 📧 Support

For questions and support, please open an issue on GitHub.
