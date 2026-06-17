from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Meta Configuration
    WHATSAPP_VERIFY_TOKEN: str = "MY_SUPER_SECRET_TOKEN"
    WHATSAPP_API_TOKEN: str = "Token" # System user access token from Meta
    WHATSAPP_PHONE_NUMBER_ID: str = "Token"

    # AWS Configuration
    AWS_REGION: str = "us-east-1"
    DYNAMODB_CART_TABLE: str = "ActiveCarts"
    DYNAMODB_HISTORY_TABLE: str = "OrderHistory"
    #BEDROCK_MODEL_ID: str = "us.meta.llama3-1-70b-instruct-v1:0"
    # Switch to Claude 3.5 Sonnet (or 'anthropic.claude-3-haiku-20240307-v1:0' for faster/cheaper testing)
    BEDROCK_MODEL_ID: str = "anthropic.claude-sonnet-4-6"
    S3_BUCKET_NAME: str = "grocery-bot-voice-vault-kunal"
    GEMINI_API_KEY: str = "AQ.Token"

    class Config:
        env_file = ".env"

settings = Settings()
