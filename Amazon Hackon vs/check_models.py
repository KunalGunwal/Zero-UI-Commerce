import boto3

# Initialize the client
client = boto3.client('bedrock', region_name="us-east-1")

# List models
response = client.list_foundation_models()

for model in response['modelSummaries']:
    if 'anthropic' in model['modelId'] and 'sonnet' in model['modelId']:
        print(f"Found Model: {model['modelId']}")