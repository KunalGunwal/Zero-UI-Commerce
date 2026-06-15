import json
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from typing import List, Optional
from app.core.config import settings

# 1. Initialize the NEW Gemini Client
client = genai.Client(api_key=settings.GEMINI_API_KEY)

# 2. Pydantic Models remain exactly the same
class GroceryItem(BaseModel):
    item: str = Field(description="The generic standardized category item name, e.g., 'pyaz', 'shampoo'")
    quantity: float = Field(default=0.0, description="Numerical value. 0 if unspecified.")
    unit: Optional[str] = Field(default=None, description="The weight unit")
    brand: Optional[str] = Field(default=None, description="The normalized brand name")
    action: str = Field(default="add", description="Must be 'add' or 'remove'")

class GroceryCart(BaseModel):
    items: List[GroceryItem]

def extract_groceries_from_text(user_text: str, existing_cart: GroceryCart = None) -> GroceryCart:
    memory_context = ""
    if existing_cart and existing_cart.items:
        memory_context = "CURRENT PENDING CART STATE (What the user already ordered):\n"
        for item in existing_cart.items:
            qty_status = item.quantity if item.quantity > 0 else "MISSING_QUANTITY"
            memory_context += f"- {item.item} (Quantity: {qty_status})\n"
        
        memory_context += (
            "\nCRITICAL CONTEXT INSTRUCTION:\n"
            "If the user says something like 'pyaz hata do' or 'remove onion', you MUST extract 'pyaz' and set its 'action' to 'remove'.\n"
            "If the user provides ONLY a number (e.g., '3kg'), apply it to the item marked MISSING_QUANTITY by outputting it with 'action': 'add'.\n\n"
        )

    system_instruction = (
        "You are a highly intelligent extraction assistant for an Indian grocery delivery WhatsApp bot. "
        "Users will send messages in Hindi, English, and Hinglish. Extract EVERY item the user mentions.\n\n"
        f"{memory_context}"
        "ROUTING RULE:\n"
        "1. Core inventory: ['pyaz', 'paneer', 'aalu', 'tomato', 'salt', 'rice', 'biryani masala']. Map to these EXACTLY if matched.\n"
        "2. Non-core items (e.g., 'macbook', 'shampoo'): extract their generic names as requested.\n\n"
        "INTENT CLASSIFICATION (CRITICAL):\n"
        "Evaluate if the user wants to ADD or REMOVE the item.\n"
        "- Words like 'hata do', 'nhi chahiye', 'remove', 'cancel', 'delete' -> action = 'remove'\n"
        "- Words like 'add', 'chahiye', 'aur', or just listing the item -> action = 'add'\n\n"
        "Translation & Typo Mapping:\n"
        "- 'pyaaz', 'piyaz', 'onion' -> 'pyaz'\n"
        "- 'alu', 'aloo', 'potato' -> 'aalu'\n"
        "- 'tamatar', 'tomato' -> 'tomato'\n"
        "- 'panir', 'paneer' -> 'paneer'\n\n"
        "CRITICAL: If a user DOES NOT specify a number, set their 'quantity' field to exactly 0."
    )

    try:
        # 3. Use the NEW client generation syntax
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=user_text,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=GroceryCart,
                temperature=0.1
            )
        )
        
        parsed_json = json.loads(response.text)
        return GroceryCart(**parsed_json)
        
    except Exception as e:
        print(f"❌ [Gemini Error] Failed to extract items: {str(e)}")
        return GroceryCart(items=[])