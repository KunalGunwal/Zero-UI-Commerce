import boto3
from app.core.config import settings

dynamodb = boto3.resource('dynamodb', region_name=settings.AWS_REGION)
catalog_table = dynamodb.Table('GroceryCatalog')

def get_item_from_catalog(category_slug: str, brand_slug: str = None):
    """
    Looks up a product using a category and optional brand identifier.
    Defaults to the standard popular option if no brand is provided.
    """
    category = category_slug.lower().strip()
    brand = brand_slug.lower().strip() if brand_slug else "generic"

    # Step 1: Attempt explicit compound lookup (e.g., 'salt_ashirvaad')
    try:
        target_sku = f"{category}_{brand}"
        response = catalog_table.get_item(Key={'sku_id': target_sku})
        if 'Item' in response:
            return response['Item']
    except Exception:
        pass

    # Step 2: Fallback if brand was missing or not found - search for default option
    try:
        defaults = {
            "salt": "salt_tata",
            "rice": "rice_daawat",
            "biryani masala": "biryani masala_mdh",
            "pyaz": "pyaz_generic",
            "aalu": "aalu_generic",
            "tomato": "tomato_generic",
            "paneer": "paneer_amul",
            "milk": "milk_amul",
            "atta": "atta_aashirvaad",
            "toor dal": "toordal_tata",
            "moong dal": "moongdal_tata",
            "oil": "oil_fortune",
            "sugar": "sugar_madhur",
            "haldi": "haldi_catch",
            "garam masala": "garam masala_mdh",
            "maggi": "maggi_nestle",
            "soap": "soap_dove",
            "shampoo": "shampoo_clinicplus",
            "toothpaste": "toothpaste_colgate",
            "detergent": "detergent_surfexcel"
        }
        
        fallback_sku = defaults.get(category, f"{category}_generic")
        response = catalog_table.get_item(Key={'sku_id': fallback_sku})
        return response.get('Item', None)
        
    except Exception as e:
        print(f"[Catalog Lookup Error] Fallback failed: {str(e)}")
        return None