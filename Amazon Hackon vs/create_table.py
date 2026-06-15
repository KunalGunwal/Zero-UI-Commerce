import boto3

def create_dynamodb_table():
    print("Connecting to AWS DynamoDB...")
    dynamodb = boto3.client('dynamodb', region_name='us-east-1')
    
    try:
        response = dynamodb.create_table(
            TableName='ActiveCarts',
            AttributeDefinitions=[
                {'AttributeName': 'phone_number', 'AttributeType': 'S'}
            ],
            KeySchema=[
                {'AttributeName': 'phone_number', 'KeyType': 'HASH'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        print(f"✅ Success! Table 'ActiveCarts' is currently: {response['TableDescription']['TableStatus']}")
        print("It will be ready to use in about 5 seconds.")
    except Exception as e:
        print(f"Error creating table: {e}")

if __name__ == "__main__":
    create_dynamodb_table()