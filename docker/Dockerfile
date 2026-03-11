# ============================================
# CreditWise 信贷风控助手 Docker Environment
# External API integration with support for multiple LLM providers
# ============================================

# Base image (no GPU needed - using external LLM API)
FROM python:3.12-slim

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Set working directory
WORKDIR /workspace

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    wget \
    vim \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install API dependencies
RUN pip install --upgrade pip && \
    pip install \
    fastapi \
    uvicorn \
    openai \
    httpx \
    python-multipart

# Install data science and analysis tools
# Data processing and analysis
RUN pip install \
    pandasql \
    pyjanitor \
    feature-engine \
    missingno

# Data visualization
RUN pip install \
    plotly \
    bokeh \
    squarify \
    matplotlib-venn \
    wordcloud \
    folium \
    contextily

# Machine learning / Statistical modeling
RUN pip install \
    mlxtend \
    imbalanced-learn \
    optuna \
    shap \
    lime

# Time series and forecasting
RUN pip install \
    prophet \
    pmdarima \
    tslearn \
    lifelines

# Bayesian / Probabilistic modeling
RUN pip install \
    pymc \
    pystan \
    cmdstanpy \
    pyro-ppl

# Causal inference
RUN pip install \
    dowhy \
    econml \
    causalml \
    CausalInference \
    zepid

# Geospatial data science
RUN pip install \
    geopandas \
    shapely \
    rasterio \
    rasterstats \
    fiona \
    rtree \
    pysal \
    libpysal \
    esda \
    giddy \
    segregation \
    spopt \
    spreg \
    spglm \
    splot \
    spaghetti \
    tobler

# Expose port for API service
EXPOSE 8000

# Default command
CMD ["/bin/bash"]
