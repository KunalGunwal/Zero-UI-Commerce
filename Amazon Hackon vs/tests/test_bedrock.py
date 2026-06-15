# test_bedrock.py
from app.services.bedrock import extract_groceries_from_text

def run_test():
    # A realistic, messy Hinglish prompt that a user might send via WhatsApp
    test_message = "bhaiya 2 kilo pyaz, 500 gram paneer, aur ek biryani masala bhej do"
    
    print(f"Testing input: '{test_message}'\n")
    print("Sending to AWS Bedrock...")
    
    # Call our function
    cart = extract_groceries_from_text(test_message)
    
    # Output the structured Pydantic model
    print("\nExtraction Success!")
    for item in cart.items:
        print(f"- {item.quantity} {item.unit} of {item.item}")

if __name__ == "__main__":
    run_test()