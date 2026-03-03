from deepanalyze import DeepAnalyzeAPI

# Initialize the API client
deepanalyze = DeepAnalyzeAPI()

# Display configuration
config = deepanalyze.get_config()
print("DeepAnalyze API Configuration:")
print(f"API Base: {config['api_base']}")
print(f"Model: {config['model_name']}")
print(f"API Key: {'Set' if config['api_key'] else 'Not Set'}")

# Note: This is just a demonstration of the API configuration
# Actual chat completions should be handled through the API endpoints
