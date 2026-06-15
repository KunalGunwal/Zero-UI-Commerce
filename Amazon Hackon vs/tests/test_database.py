# tests/test_database.py
from app.services.bedrock import extract_groceries_from_text
from app.services.database import update_cart, get_cart, clear_cart

def run_test():
    test_phone = "919876543210"
    
    # 1. Start with a clean slate
    print("🧹 Clearing any old test data...")
    clear_cart(test_phone)
    
    # 2. Simulate Message 1
    msg_1 = "bhaiya 2 kilo pyaz aur 500 gram paneer"
    print(f"\n📲 [Message 1 Received]: '{msg_1}'")
    cart_1 = extract_groceries_from_text(msg_1)
    update_cart(test_phone, cart_1)
    
    # 3. Simulate Message 2 (User forgot something)
    msg_2 = "oh aur ek biryani masala ka packet bhi rakh dena"
    print(f"\n📲 [Message 2 Received]: '{msg_2}'")
    cart_2 = extract_groceries_from_text(msg_2)
    update_cart(test_phone, cart_2)
    
    # 4. Fetch the final aggregated memory
    print("\n🛒 --- FINAL CART IN DYNAMODB ---")
    final_cart = get_cart(test_phone)
    for item in final_cart.get('items', []):
        print(f"- {item['quantity']} {item['unit']} of {item['item']}")

if __name__ == "__main__":
    run_test()