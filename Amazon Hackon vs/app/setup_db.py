import boto3
from app.core.config import settings

def setup_massive_catalog():
    dynamodb = boto3.resource('dynamodb', region_name=settings.AWS_REGION)
    
    print("⏳ Re-creating massive GroceryCatalog table...")
    try:
        try:
            old_table = dynamodb.Table('GroceryCatalog')
            old_table.delete()
            old_table.meta.client.get_waiter('table_not_exists').wait(TableName='GroceryCatalog')
            print("🗑️ Old table cleared.")
        except Exception:
            pass

        table = dynamodb.create_table(
            TableName='GroceryCatalog',
            KeySchema=[{'AttributeName': 'sku_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'sku_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        table.meta.client.get_waiter('table_exists').wait(TableName='GroceryCatalog')
        print("✅ New Catalog Table created!")
        
        # MASSIVE SEED INVENTORY
        inventory_data = [
            # ==========================================
            # 1. FRESH PRODUCE (Unbranded)
            # ==========================================
            {"sku_id": "pyaz_generic", "category": "pyaz", "brand": "none", "display_name": "Fresh Onion (Pyaz)", "price_per_unit": 40, "unit": "kg", "is_branded": False},
            {"sku_id": "aalu_generic", "category": "aalu", "brand": "none", "display_name": "Fresh Potato (Aalu)", "price_per_unit": 30, "unit": "kg", "is_branded": False},
            {"sku_id": "tomato_generic", "category": "tomato", "brand": "none", "display_name": "Desi Tomato (Tamatar)", "price_per_unit": 60, "unit": "kg", "is_branded": False},
            {"sku_id": "mirchi_generic", "category": "mirchi", "brand": "none", "display_name": "Green Chilli (Hari Mirch)", "price_per_unit": 80, "unit": "kg", "is_branded": False},
            {"sku_id": "dhaniya_generic", "category": "dhaniya", "brand": "none", "display_name": "Fresh Coriander (Dhaniya)", "price_per_unit": 20, "unit": "bunch", "is_branded": False},
            {"sku_id": "nimbu_generic", "category": "nimbu", "brand": "none", "display_name": "Fresh Lemon (Nimbu)", "price_per_unit": 5, "unit": "piece", "is_branded": False},
            {"sku_id": "adrak_generic", "category": "adrak", "brand": "none", "display_name": "Fresh Ginger (Adrak)", "price_per_unit": 120, "unit": "kg", "is_branded": False},
            {"sku_id": "lahsun_generic", "category": "lahsun", "brand": "none", "display_name": "Garlic (Lahsun)", "price_per_unit": 150, "unit": "kg", "is_branded": False},

            # ==========================================
            # 2. DAIRY & BAKERY
            # ==========================================
            {"sku_id": "milk_amul", "category": "milk", "brand": "amul", "display_name": "Amul Taaza Milk", "price_per_unit": 33, "unit": "500ml", "is_branded": True, "is_default": True},
            {"sku_id": "milk_motherdairy", "category": "milk", "brand": "motherdairy", "display_name": "Mother Dairy Toned Milk", "price_per_unit": 33, "unit": "500ml", "is_branded": True, "is_default": False},
            {"sku_id": "paneer_amul", "category": "paneer", "brand": "amul", "display_name": "Amul Malai Paneer", "price_per_unit": 85, "unit": "200g", "is_branded": True, "is_default": True},
            {"sku_id": "paneer_generic", "category": "paneer", "brand": "none", "display_name": "Fresh Dairy Paneer", "price_per_unit": 350, "unit": "kg", "is_branded": False, "is_default": False},
            {"sku_id": "butter_amul", "category": "butter", "brand": "amul", "display_name": "Amul Butter", "price_per_unit": 58, "unit": "100g", "is_branded": True, "is_default": True},
            {"sku_id": "dahi_amul", "category": "dahi", "brand": "amul", "display_name": "Amul Masti Dahi", "price_per_unit": 35, "unit": "400g", "is_branded": True, "is_default": True},
            {"sku_id": "bread_britannia", "category": "bread", "brand": "britannia", "display_name": "Britannia White Bread", "price_per_unit": 40, "unit": "packet", "is_branded": True, "is_default": True},
            {"sku_id": "eggs_generic", "category": "eggs", "brand": "none", "display_name": "Fresh White Eggs", "price_per_unit": 48, "unit": "6-pack", "is_branded": False},

            # ==========================================
            # 3. STAPLES (Rice, Flour, Dal, Oil)
            # ==========================================
            {"sku_id": "atta_aashirvaad", "category": "atta", "brand": "aashirvaad", "display_name": "Aashirvaad Shudh Chakki Atta", "price_per_unit": 230, "unit": "5kg", "is_branded": True, "is_default": True},
            {"sku_id": "atta_fortune", "category": "atta", "brand": "fortune", "display_name": "Fortune Chakki Fresh Atta", "price_per_unit": 210, "unit": "5kg", "is_branded": True, "is_default": False},
            {"sku_id": "rice_daawat", "category": "rice", "brand": "daawat", "display_name": "Daawat Rozana Basmati Rice", "price_per_unit": 110, "unit": "kg", "is_branded": True, "is_default": True},
            {"sku_id": "rice_indiagate", "category": "rice", "brand": "indiagate", "display_name": "India Gate Basmati Rice", "price_per_unit": 125, "unit": "kg", "is_branded": True, "is_default": False},
            {"sku_id": "toordal_tata", "category": "toor dal", "brand": "tata", "display_name": "Tata Sampann Toor Dal", "price_per_unit": 160, "unit": "kg", "is_branded": True, "is_default": True},
            {"sku_id": "moongdal_tata", "category": "moong dal", "brand": "tata", "display_name": "Tata Sampann Moong Dal", "price_per_unit": 140, "unit": "kg", "is_branded": True, "is_default": True},
            {"sku_id": "oil_fortune", "category": "oil", "brand": "fortune", "display_name": "Fortune Sunlite Refined Oil", "price_per_unit": 145, "unit": "1L", "is_branded": True, "is_default": True},
            {"sku_id": "oil_saffola", "category": "oil", "brand": "saffola", "display_name": "Saffola Gold Cooking Oil", "price_per_unit": 180, "unit": "1L", "is_branded": True, "is_default": False},
            {"sku_id": "sugar_madhur", "category": "sugar", "brand": "madhur", "display_name": "Madhur Pure & Hygienic Sugar", "price_per_unit": 55, "unit": "kg", "is_branded": True, "is_default": True},
            {"sku_id": "sugar_generic", "category": "sugar", "brand": "none", "display_name": "Loose Sugar (Chini)", "price_per_unit": 45, "unit": "kg", "is_branded": False, "is_default": False},
            {"sku_id": "salt_tata", "category": "salt", "brand": "tata", "display_name": "Tata Salt Premium", "price_per_unit": 28, "unit": "packet", "is_branded": True, "is_default": True},
            {"sku_id": "salt_aashirvaad", "category": "salt", "brand": "aashirvaad", "display_name": "Aashirvaad Iodized Salt", "price_per_unit": 25, "unit": "packet", "is_branded": True, "is_default": False},

            # ==========================================
            # 4. SPICES & CONDIMENTS
            # ==========================================
            {"sku_id": "biryani masala_mdh", "category": "biryani masala", "brand": "mdh", "display_name": "MDH Biryani Masala", "price_per_unit": 45, "unit": "packet", "is_branded": True, "is_default": True},
            {"sku_id": "biryani masala_everest", "category": "biryani masala", "brand": "everest", "display_name": "Everest Shahi Biryani Masala", "price_per_unit": 50, "unit": "packet", "is_branded": True, "is_default": False},
            {"sku_id": "paneer masala_everest", "category": "paneer masala", "brand": "everest", "display_name": "Everest Paneer Masala", "price_per_unit": 45, "unit": "packet", "is_branded": True, "is_default": True},
            {"sku_id": "haldi_catch", "category": "haldi", "brand": "catch", "display_name": "Catch Turmeric Powder (Haldi)", "price_per_unit": 35, "unit": "100g", "is_branded": True, "is_default": True},
            {"sku_id": "mirchi powder_everest", "category": "mirchi powder", "brand": "everest", "display_name": "Everest Tikhalal Chilli Powder", "price_per_unit": 42, "unit": "100g", "is_branded": True, "is_default": True},
            {"sku_id": "garam masala_mdh", "category": "garam masala", "brand": "mdh", "display_name": "MDH Garam Masala", "price_per_unit": 55, "unit": "100g", "is_branded": True, "is_default": True},
            {"sku_id": "ketchup_kissan", "category": "ketchup", "brand": "kissan", "display_name": "Kissan Fresh Tomato Ketchup", "price_per_unit": 120, "unit": "1kg", "is_branded": True, "is_default": True},

            # ==========================================
            # 5. SNACKS & BEVERAGES
            # ==========================================
            {"sku_id": "maggi_nestle", "category": "maggi", "brand": "nestle", "display_name": "Maggi 2-Minute Noodles", "price_per_unit": 14, "unit": "packet", "is_branded": True, "is_default": True},
            {"sku_id": "biscuits_parle", "category": "biscuits", "brand": "parle", "display_name": "Parle-G Gold Biscuits", "price_per_unit": 20, "unit": "packet", "is_branded": True, "is_default": True},
            {"sku_id": "tea_tata", "category": "tea", "brand": "tata", "display_name": "Tata Tea Premium", "price_per_unit": 150, "unit": "250g", "is_branded": True, "is_default": True},
            {"sku_id": "coffee_nescafe", "category": "coffee", "brand": "nescafe", "display_name": "Nescafe Classic Coffee", "price_per_unit": 165, "unit": "50g", "is_branded": True, "is_default": True},

            # ==========================================
            # 6. PERSONAL CARE & HOUSEHOLD
            # ==========================================
            {"sku_id": "soap_dove", "category": "soap", "brand": "dove", "display_name": "Dove Cream Beauty Bathing Bar", "price_per_unit": 65, "unit": "bar", "is_branded": True, "is_default": True},
            {"sku_id": "soap_lifebuoy", "category": "soap", "brand": "lifebuoy", "display_name": "Lifebuoy Total 10 Soap", "price_per_unit": 35, "unit": "bar", "is_branded": True, "is_default": False},
            {"sku_id": "shampoo_clinicplus", "category": "shampoo", "brand": "clinicplus", "display_name": "Clinic Plus Strong & Long Shampoo", "price_per_unit": 110, "unit": "bottle", "is_branded": True, "is_default": True},
            {"sku_id": "toothpaste_colgate", "category": "toothpaste", "brand": "colgate", "display_name": "Colgate Strong Teeth", "price_per_unit": 95, "unit": "100g", "is_branded": True, "is_default": True},
            {"sku_id": "detergent_surfexcel", "category": "detergent", "brand": "surfexcel", "display_name": "Surf Excel Easy Wash Detergent", "price_per_unit": 130, "unit": "1kg", "is_branded": True, "is_default": True},
            {"sku_id": "cleaner_harpic", "category": "cleaner", "brand": "harpic", "display_name": "Harpic Power Plus Toilet Cleaner", "price_per_unit": 99, "unit": "500ml", "is_branded": True, "is_default": True}
        ]
        
        # Batch writing to DynamoDB
        with table.batch_writer() as batch:
            for item in inventory_data:
                batch.put_item(Item=item)
                
        print(f"🌱 Successfully seeded {len(inventory_data)} items into the catalog!")
        
    except Exception as e:
        print(f"❌ Error setting up database: {str(e)}")

if __name__ == "__main__":
    setup_massive_catalog()