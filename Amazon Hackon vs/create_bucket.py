import boto3
from app.core.config import settings

def make_s3_bucket():
    s3 = boto3.client('s3', region_name=settings.AWS_REGION)
    # Generate a completely unique bucket name for your hackathon account
    bucket_name = f"grocery-bot-voice-vault-{int(settings.WHATSAPP_VERIFY_TOKEN[-5:]) if settings.WHATSAPP_VERIFY_TOKEN.isdigit() else 'kunal'}"
    
    try:
        s3.create_bucket(Bucket=bucket_name)
        print(f"✅ Created S3 Bucket: {bucket_name}")
        print("Add this line to your project config/environment later.")
    except Exception as e:
        print(f"Bucket Creation Warning/Error: {e}")

if __name__ == "__main__":
    make_s3_bucket()