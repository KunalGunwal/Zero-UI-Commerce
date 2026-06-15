import boto3
import json
import time
from decimal import Decimal
from app.core.config import settings
from app.services.bedrock import GroceryCart, GroceryItem

dynamodb = boto3.resource('dynamodb', region_name=settings.AWS_REGION)
carts_table = dynamodb.Table('ActiveCarts')

def get_cart(phone_number: str) -> GroceryCart:
    try:
        response = carts_table.get_item(Key={'phone_number': phone_number})
        if 'Item' in response and 'items' in response['Item']:
            items = [GroceryItem(**i) for i in response['Item']['items']]
            return GroceryCart(items=items)
    except Exception as e:
        print(f"Error reading cart: {str(e)}")
    return GroceryCart(items=[])

def update_cart(phone_number: str, cart: GroceryCart):
    try:
        items_dict = [item.dict() for item in cart.items]
        items_dict_safe = json.loads(json.dumps(items_dict), parse_float=Decimal)
        carts_table.put_item(
            Item={
                'phone_number': phone_number,
                'items': items_dict_safe
            }
        )
        return cart
    except Exception as e:
        print(f"Error updating cart: {str(e)}")

def clear_cart(phone_number: str):
    try:
        carts_table.delete_item(Key={'phone_number': phone_number})
    except Exception as e:
        print(f"Error clearing cart: {str(e)}")

# ==========================================
# ADMIN DASHBOARD DATABASE FUNCTIONS
# ==========================================
def save_order_history(phone_number: str, cart: GroceryCart):
    try:
        items_dict = [item.dict() for item in cart.items]
        items_dict_safe = json.loads(json.dumps(items_dict), parse_float=Decimal)
        carts_table.put_item(
            Item={
                'phone_number': f"{phone_number}_history",
                'items': items_dict_safe,
                'status': "PACKING", 
                'payment_status': "UNPAID", 
                'timestamp': int(time.time())
            }
        )
    except Exception as e:
        print(f"Error saving history: {str(e)}")

def mark_order_paid(phone_number: str):
    try:
        carts_table.update_item(
            Key={'phone_number': f"{phone_number}_history"},
            UpdateExpression="set payment_status = :p",
            ExpressionAttributeValues={':p': 'PAID'}
        )
    except Exception as e:
        print(f"Error marking paid: {str(e)}")

def get_order_history(phone_number: str) -> GroceryCart:
    try:
        response = carts_table.get_item(Key={'phone_number': f"{phone_number}_history"})
        if 'Item' in response and 'items' in response['Item']:
            items = [GroceryItem(**i) for i in response['Item']['items']]
            for item in items:
                item.action = 'add'
            return GroceryCart(items=items)
    except Exception as e:
        pass
    return None

def update_order_status(phone_number: str, new_status: str):
    try:
        carts_table.update_item(
            Key={'phone_number': f"{phone_number}_history"},
            UpdateExpression="set #s = :s",
            ExpressionAttributeNames={'#s': 'status'},
            ExpressionAttributeValues={':s': new_status}
        )
    except Exception as e:
        print(f"Error updating status: {str(e)}")

def delete_order_history(phone_number: str):
    try:
        carts_table.delete_item(Key={'phone_number': f"{phone_number}_history"})
    except Exception as e:
        print(f"Error deleting history: {str(e)}")

def get_all_orders_for_admin():
    try:
        response = carts_table.scan()
        return response.get('Items', [])
    except Exception as e:
        print(f"Error scanning table for admin: {str(e)}")
        return []