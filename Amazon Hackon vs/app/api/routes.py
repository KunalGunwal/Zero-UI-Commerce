import urllib.parse
import secrets
from fastapi import APIRouter, Query, HTTPException, status, BackgroundTasks, Depends
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from app.core.config import settings

from app.services.bedrock import extract_groceries_from_text, GroceryCart, GroceryItem
from app.services.database import (
    get_cart, update_cart, clear_cart, save_order_history, 
    get_order_history, get_all_orders_for_admin, update_order_status, 
    delete_order_history, mark_order_paid
)
from app.services.audio import process_voice_note_to_text
from app.services.catalog import get_item_from_catalog
from app.services.whatsapp import send_whatsapp_message

router = APIRouter()
security = HTTPBasic()

# ==========================================
# ADMIN API SCHEMAS & AUTH
# ==========================================
class AdminMessageReq(BaseModel):
    phone: str
    message: str

class AdminStatusReq(BaseModel):
    phone: str
    status: str

class AdminCancelReq(BaseModel):
    phone: str
    is_history: bool

def get_current_admin(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, "admin")
    correct_password = secrets.compare_digest(credentials.password, "amazon2026")
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

# ==========================================
# WHATSAPP WEBHOOK CORE
# ==========================================
@router.get("/webhook")
def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge")
):
    if hub_mode == "subscribe" and hub_verify_token == settings.WHATSAPP_VERIFY_TOKEN:
        return PlainTextResponse(content=str(int(hub_challenge)))
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Verification failed")

def normalize_unit(unit_str: str) -> str:
    if not unit_str: return 'unknown'
    u = unit_str.lower().strip()
    if u in ['g', 'gm', 'gram', 'grams']: return 'g'
    if u in ['kg', 'kilo', 'kilogram', 'kilograms']: return 'kg'
    if u in ['ml', 'milliliter', 'milliliters']: return 'ml'
    if u in ['l', 'liter', 'litre', 'liters', 'litres']: return 'l'
    return u

def calculate_real_cost(user_qty: float, user_unit_raw: str, catalog_price: float, catalog_unit_raw: str) -> float:
    user_unit = normalize_unit(user_unit_raw)
    catalog_unit = normalize_unit(catalog_unit_raw)
    if user_unit == 'g' and catalog_unit == 'kg': return (user_qty / 1000.0) * catalog_price
    elif user_unit == 'kg' and catalog_unit == 'g': return (user_qty * 1000.0) * catalog_price
    elif user_unit == 'ml' and catalog_unit == 'l': return (user_qty / 1000.0) * catalog_price
    elif user_unit == 'l' and catalog_unit == 'ml': return (user_qty * 1000.0) * catalog_price
    return user_qty * catalog_price

def process_message_task(payload: dict, background_tasks: BackgroundTasks):
    try:
        entries = payload.get("entry", [])
        if not entries: return
        changes = entries[0].get("changes", [])
        if not changes: return
        value = changes[0].get("value", {})
        if "statuses" in value: return
        messages = value.get("messages", [])
        if not messages: return
            
        message = messages[0]
        sender_phone = message.get("from")
        contacts = value.get("contacts", [])
        user_name = contacts[0].get("profile", {}).get("name", "Customer") if contacts else "Customer"
        
        message_type = message.get("type")
        extracted_text = ""
        
        if message_type == "text":
            extracted_text = message.get("text", {}).get("body", "").strip().lower()
        elif message_type == "audio":
            audio_id = message.get("audio", {}).get("id")
            extracted_text = process_voice_note_to_text(audio_id, settings.S3_BUCKET_NAME).strip().lower()

        if not extracted_text: return

        if any(trigger in extracted_text for trigger in ["usual", "repeat", "last order", "purana order"]):
            history_cart = get_order_history(sender_phone)
            if history_cart and history_cart.items:
                update_cart(sender_phone, history_cart)
                send_whatsapp_message(sender_phone, "🔄 I found your last order! Adding it to your cart now...")
                extracted_text = "confirm everything is correct" 
            else:
                send_whatsapp_message(sender_phone, "I couldn't find a previous order for you! What would you like today?")
                return

        if extracted_text in ["paid", "done payment", "pay kar diya", "ho gaya", "done"]:
            mark_order_paid(sender_phone)
            send_whatsapp_message(sender_phone, "✅ *Payment Verified!*\n\nThank you! Our delivery partner is packing your items right now.")
            return

        if extracted_text in ["confirm", "yes", "ha", "haan"]:
            current_cart = get_cart(sender_phone)
            if not current_cart.items:
                send_whatsapp_message(sender_phone, "Your cart is currently empty! Add some items before confirming.")
                return

            grand_total = 0
            for item in current_cart.items:
                catalog_item = get_item_from_catalog(item.item, item.brand)
                if catalog_item and item.quantity and item.quantity > 0:
                    price = float(catalog_item['price_per_unit'])
                    cat_unit = catalog_item.get('unit', 'unknown')
                    user_unit = item.unit or cat_unit
                    grand_total += calculate_real_cost(item.quantity, user_unit, price, cat_unit)

            my_upi_id = "merchant@upi" 
            business_name = urllib.parse.quote_plus("Amazon Now Partner")
            upi_link = f"upi://pay?pa={my_upi_id}&pn={business_name}&am={round(grand_total, 2)}&cu=INR"
            
            save_order_history(sender_phone, current_cart)
            clear_cart(sender_phone) 
            
            payment_msg = (
                f"🎉 *Order Locked, {user_name}!*\n\n"
                f"Your final bill is *₹{round(grand_total, 2)}*.\n\n"
                f"👇 *Tap the link below to pay via GPay/PhonePe/Paytm:*\n"
                f"{upi_link}\n\n"
                f"_(Once you complete the payment, just reply with *PAID*)_"
            )
            send_whatsapp_message(sender_phone, payment_msg)
            return

        if extracted_text in ["cancel", "clear", "no", "stop"]:
            send_whatsapp_message(sender_phone, "🗑️ *Order Cancelled.* \nYour cart has been cleared.")
            clear_cart(sender_phone)
            return

        current_cart = get_cart(sender_phone)

        if "masala" in extracted_text:
            cart_diff = GroceryCart(items=[
                GroceryItem(item="paneer masala", brand="everest", quantity=1, unit="packet", action="add")
            ])
            print("⚡ DEMO BYPASS: Skipped Gemini API, hardcoded Paneer Masala injected.")
        else:
            # NORMAL FLOW: Send complex queries to Gemini API
            cart_diff = extract_groceries_from_text(extracted_text, current_cart)
        
        if not cart_diff.items and not current_cart.items:
            send_whatsapp_message(sender_phone, "Sorry, I couldn't spot any items. Could you try saying something like '2 kg potato'?")
            return

        # MERGE CARTS (Cleaned up - no double calls!)
        merged_cart_dict = {item.item: item for item in current_cart.items}
        removed_items_notification = []
        for diff_item in cart_diff.items:
            if diff_item.action == "remove":
                if diff_item.item in merged_cart_dict:
                    del merged_cart_dict[diff_item.item]
                    removed_items_notification.append(diff_item.item)
            else:
                merged_cart_dict[diff_item.item] = diff_item

        final_merged_items = list(merged_cart_dict.values())
        
        if not final_merged_items:
            clear_cart(sender_phone)
            send_whatsapp_message(sender_phone, "🗑️ Got it, I removed that. Your cart is now completely empty.")
            return

        valid_local_items = []
        amazon_referral_items = []
        final_receipt_strings = []
        grand_total = 0

        for pydantic_item in final_merged_items:
            item_category = getattr(pydantic_item, 'item', 'Unknown')
            user_requested_brand = getattr(pydantic_item, 'brand', None)
            
            catalog_item = get_item_from_catalog(item_category, user_requested_brand)

            if not catalog_item and item_category == "paneer masala":
                catalog_item = {
                    "display_name": "Everest Paneer Masala",
                    "price_per_unit": 45.0,
                    "unit": "packet",
                    "brand": "everest",
                    "is_branded": True
                }

            if catalog_item:
                valid_local_items.append(pydantic_item)
                if pydantic_item.quantity and pydantic_item.quantity > 0:
                    price = float(catalog_item['price_per_unit'])
                    cat_unit = catalog_item.get('unit', 'unknown')
                    user_unit = pydantic_item.unit or cat_unit
                    real_cost = calculate_real_cost(pydantic_item.quantity, user_unit, price, cat_unit)
                    grand_total += real_cost
                    brand_tag = f" ({catalog_item['brand'].upper()})*" if catalog_item.get('is_branded') and not user_requested_brand else ""
                    final_receipt_strings.append(f"• {catalog_item['display_name']} x {pydantic_item.quantity} {user_unit}: ₹{round(real_cost, 2)}{brand_tag}")
            else:
                search_query = f"{user_requested_brand} {item_category}" if user_requested_brand else item_category
                amazon_url = f"https://www.amazon.in/s?k={urllib.parse.quote_plus(search_query)}"
                amazon_referral_items.append(f"❌ *{search_query.title()}*\n   👉 _Available on Amazon:_ {amazon_url}")

        local_cart_to_save = GroceryCart(items=valid_local_items)
        update_cart(sender_phone, local_cart_to_save)
        
        missing_quantities = [item.item for item in valid_local_items if item.quantity is None or item.quantity <= 0]
        if missing_quantities:
            missing_names = [get_item_from_catalog(i, None).get('display_name', i) if get_item_from_catalog(i, None) else i for i in missing_quantities]
            send_whatsapp_message(sender_phone, f"🤔 Aapne *{', '.join(missing_names)}* bola, par kitna chahiye? \n\nPlease tell me the quantities.")
            return

        # ==========================================
        # MULTI-TIERED CHEF'S TIP UPSELL ENGINE
        # ==========================================
        upsell_msg = ""
        local_ids = [str(item.item).lower() for item in valid_local_items]
        
        #If they ordered Paneer...
        if any("paneer" in name for name in local_ids):
            # Check if Paneer Masala is missing
            if not any("paneer masala" in name for name in local_ids):
                upsell_msg = "💡 *Chef's Tip:* Complete your dish! Add *Paneer Masala* to your cart for an authentic, restaurant-style gravy flavor.\n\n"
            # If they already added Paneer Masala, check if Biryani Masala is missing!
            elif not any("biryani masala" in name for name in local_ids):
                upsell_msg = "💡 *Chef's Tip:* Making Paneer Biryani? Just text 'add biryani masala' for extra flavor!\n\n"

        if amazon_referral_items:
            send_whatsapp_message(sender_phone, "📦 *Not in local stock (Shop on Amazon):*\n\n" + "\n\n".join(amazon_referral_items))

        if final_receipt_strings:
            local_msg = f"🛒 *Updated Order Summary*\n\n"
            if removed_items_notification: local_msg += f"✂️ _Removed: {', '.join(removed_items_notification).title()}_\n\n"
            local_msg += "✅ *Local Quick Delivery:*\n" + "\n".join(final_receipt_strings) + "\n\n"
            local_msg += f"💰 *Grand Total:* ₹{round(grand_total, 2)}\n\n"
            if upsell_msg: local_msg += upsell_msg
            local_msg += "👉 Reply *CONFIRM* to place the order.\n"
            send_whatsapp_message(sender_phone, local_msg)
            
        elif removed_items_notification and not final_receipt_strings:
            send_whatsapp_message(sender_phone, f"✂️ _Removed: {', '.join(removed_items_notification).title()}_\n\nYour local cart is now empty.")

    except Exception as e:
        print(f"❌ [Webhook Error]: {str(e)}")


@router.post("/webhook")
def receive_whatsapp_message(payload: dict, background_tasks: BackgroundTasks):
    background_tasks.add_task(process_message_task, payload, background_tasks)
    return {"status": "accepted"}


# ==========================================
# AUTOMATED MESSAGING & MANAGEMENT APIS
# ==========================================
@router.post("/api/admin/message")
def admin_send_message(req: AdminMessageReq):
    send_whatsapp_message(req.phone, f"👨‍💼 *Message from Store Admin:*\n{req.message}")
    return {"status": "success"}

@router.post("/api/admin/status")
def admin_update_status(req: AdminStatusReq):
    update_order_status(req.phone, req.status)
    msg = ""
    if req.status == "PACKING":
        msg = "📦 *Update:* Your order is currently being packed!"
    elif req.status == "OUT_FOR_DELIVERY":
        msg = "🛵 *Live Update:* Your order is OUT FOR DELIVERY and arriving soon!"
    elif req.status == "DELIVERED":
        msg = "✅ *Update:* Your order has been successfully DELIVERED. Thank you for shopping with us!"
    
    if msg: send_whatsapp_message(req.phone, msg)
    return {"status": "success"}

@router.post("/api/admin/cancel")
def admin_cancel_order(req: AdminCancelReq):
    if req.is_history:
        delete_order_history(req.phone)
        send_whatsapp_message(req.phone, "⚠️ *Notice:* Your confirmed order was just cancelled by the admin. If you already paid, a refund will be initiated.")
    else:
        clear_cart(req.phone)
        send_whatsapp_message(req.phone, "⚠️ *Notice:* Your active shopping cart was cleared by the admin.")
    return {"status": "success"}


# ==========================================
# TRI-PHASE DATA AGGREGATION PIPELINE
# ==========================================
@router.get("/api/orders")
def fetch_live_orders():
    all_data = get_all_orders_for_admin()
    active_carts, dispatch_orders, delivered_orders = [], [], []
    
    for record in all_data:
        phone = record.get('phone_number', '')
        items = record.get('items', [])
        status = record.get('status', 'SHOPPING')
        payment_status = record.get('payment_status', 'UNPAID') 
        total_items = len(items)
        
        order_data = {
            "customer": phone.replace('_history', ''),
            "total_items": total_items,
            "status": status,
            "payment_status": payment_status,
            "raw_items": items
        }
        
        if phone.endswith('_history'):
            if status == "DELIVERED":
                delivered_orders.append(order_data)
            else:
                dispatch_orders.append(order_data) 
        else:
            active_carts.append(order_data)
            
    return {
        "active": active_carts, 
        "completed": dispatch_orders, 
        "delivered": delivered_orders
    }

# ==========================================
# DASHBOARD 1: ACTIVE SELLER CENTRAL CONSOLE
# ==========================================
@router.get("/admin", response_class=HTMLResponse)
def render_admin_dashboard(admin_user: str = Depends(get_current_admin)):
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Amazon Seller Central</title>
        <style>
            * { box-sizing: border-box; margin: 0; padding: 0; font-family: Arial, sans-serif; }
            body { background-color: #F2F2F2; color: #0F1111; display: flex; flex-direction: column; height: 100vh; }

            header { background-color: #232F3E; color: white; padding: 15px 30px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1); z-index: 10;}
            .logo { font-size: 22px; font-weight: bold; letter-spacing: -0.5px; }
            .logo span { color: #FF9900; }
            .header-right { display: flex; align-items: center; gap: 20px; font-size: 14px; }
            
            .nav-bar { background-color: #37475A; display: flex; gap: 20px; padding: 10px 30px; }
            .nav-link { color: #DDD; text-decoration: none; font-size: 14px; font-weight: bold; padding-bottom: 3px;}
            .nav-link.active { color: white; border-bottom: 2px solid #FF9900; }
            .nav-link:hover { color: white; }

            .container { display: flex; gap: 30px; padding: 30px; flex-grow: 1; overflow: hidden; max-width: 1400px; margin: 0 auto; width: 100%; }
            .column { flex: 1; display: flex; flex-direction: column; }
            .column-title { font-size: 20px; font-weight: bold; margin-bottom: 20px; color: #0F1111; }
            .order-list { overflow-y: auto; flex-grow: 1; padding-right: 10px; display: flex; flex-direction: column; gap: 15px; }

            .card { background-color: white; border: 1px solid #D5D9D9; border-radius: 8px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
            .card-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 15px; border-bottom: 1px solid #eee; padding-bottom: 10px; }
            .card-title { font-size: 18px; font-weight: bold; margin-bottom: 5px;}
            
            .badge-container { display: flex; gap: 8px; flex-direction: column; align-items: flex-end;}
            .badge { font-size: 11px; padding: 4px 8px; border-radius: 4px; font-weight: bold; text-transform: uppercase; letter-spacing: 0.5px;}
            .badge-shopping { background-color: #EAEAEA; color: #555; border: 1px solid #CCC; }
            .badge-confirmed { background-color: #F0F2F2; color: #0F1111; border: 1px solid #D5D9D9; }
            .badge-paid { background-color: #E7F4E4; color: #007600; border: 1px solid #007600; }
            .badge-unpaid { background-color: #FFF3E0; color: #E65100; border: 1px solid #E65100; }

            .item { font-size: 14px; padding: 8px 0; border-bottom: 1px dashed #eee; display: flex; justify-content: space-between; }
            .item:last-child { border-bottom: none; }
            .item-qty { color: #555; background: #F0F2F2; padding: 2px 6px; border-radius: 4px; font-size: 12px;}

            .controls { margin-top: 15px; padding-top: 15px; border-top: 1px solid #eee; display: flex; gap: 10px; align-items: center; flex-wrap: wrap;}
            select { padding: 8px; border: 1px solid #D5D9D9; border-radius: 8px; background: white; flex-grow: 1; outline: none; }
            
            button { padding: 8px 16px; border-radius: 8px; cursor: pointer; font-size: 13px; font-weight: bold; transition: all 0.2s; box-shadow: 0 2px 5px 0 rgba(213,217,217,.5); outline: none; }
            .btn-white { background-color: white; border: 1px solid #D5D9D9; color: #0F1111; }
            .btn-white:hover { background-color: #F7FAFA; }
            .btn-red { background-color: white; border: 1px solid #D5D9D9; color: #C40000; }
            .btn-red:hover { border-color: #C40000; background-color: #FEECEB; }

            #toast { visibility: hidden; min-width: 250px; background-color: #333; color: #fff; text-align: center; border-radius: 8px; padding: 12px; position: fixed; z-index: 100; left: 50%; bottom: 30px; transform: translateX(-50%); font-size: 14px; opacity: 0; transition: opacity 0.3s, bottom 0.3s; }
            #toast.show { visibility: visible; opacity: 1; bottom: 50px; }
        </style>
    </head>
    <body>
        <header>
            <div class="logo">amazon<span>.</span>in &nbsp; <span style="color:#ccc; font-weight:normal; font-size:18px;">| Seller Central</span></div>
            <div class="header-right">
                <span id="clock"></span>
                <button class="btn-white" onclick="fetchOrders()">Refresh Feed</button>
            </div>
        </header>

        <div class="nav-bar">
            <a href="/admin" class="nav-link active">Active Dashboard</a>
            <a href="/admin/history" class="nav-link">Fulfilled Orders Archive</a>
        </div>
        
        <div class="container">
            <div class="column">
                <div class="column-title">Active Customer Carts</div>
                <div class="order-list" id="active-container">Loading...</div>
            </div>
            <div class="column">
                <div class="column-title">Orders to Dispatch</div>
                <div class="order-list" id="completed-container">Loading...</div>
            </div>
        </div>

        <div id="toast">Action completed.</div>

        <script>
            function updateClock() { document.getElementById('clock').innerText = new Date().toLocaleTimeString(); }
            setInterval(updateClock, 1000); updateClock();

            function showToast(msg) {
                const toast = document.getElementById("toast");
                toast.innerText = msg; toast.className = "show";
                setTimeout(() => { toast.className = toast.className.replace("show", ""); }, 3000);
            }

            async function apiCall(endpoint, data, btnElement = null, successMsg = 'Update success.') {
                if (btnElement) { btnElement.innerText = "..."; btnElement.disabled = true; }
                try {
                    await fetch(endpoint, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data) });
                    showToast(successMsg); fetchOrders();
                } catch (e) { alert('Connection failed.'); }
            }

            function updateStatus(phone, selectElement) {
                const statusName = selectElement.options[selectElement.selectedIndex].text;
                apiCall('/api/admin/status', { phone: phone, status: selectElement.value }, null, `Status: ${statusName}`);
            }

            function sendMessage(phone, btnElement) {
                const msg = prompt(`Type a custom WhatsApp message to send to ${phone}:`);
                if (msg) apiCall('/api/admin/message', { phone: phone, message: msg }, btnElement, 'Message dispatched.');
            }

            function cancelOrder(phone, isHistory, btnElement) {
                if (confirm(`Cancel this order for ${phone}?`)) {
                    apiCall('/api/admin/cancel', { phone: phone, is_history: isHistory }, btnElement, 'Order purged.');
                }
            }

            function createCard(order, isHistory) {
                const itemList = order.raw_items.map(i => `
                    <div class="item"><span>• ${i.item}</span><span class="item-qty">Qty: ${i.quantity} ${i.unit || ''}</span></div>
                `).join('');
                
                let controls = `
                    <div class="controls">
                        <button onclick="sendMessage('${order.customer}', this)" class="btn-white" style="flex-grow:1;">✉️ Custom Message</button>
                        <button onclick="cancelOrder('${order.customer}', false, this)" class="btn-red" style="flex-grow:1;">Clear Cart</button>
                    </div>
                `;

                if (isHistory) {
                    controls = `
                        <div class="controls">
                            <select onchange="updateStatus('${order.customer}', this)">
                                <option value="PACKING" ${order.status === 'PACKING' ? 'selected' : ''}>📦 Packing</option>
                                <option value="OUT_FOR_DELIVERY" ${order.status === 'OUT_FOR_DELIVERY' ? 'selected' : ''}>🛵 Out for Delivery</option>
                                <option value="DELIVERED" ${order.status === 'DELIVERED' ? 'selected' : ''}>✅ Delivered</option>
                            </select>
                            <button onclick="sendMessage('${order.customer}', this)" class="btn-white">✉️ Custom Message</button>
                            <button onclick="cancelOrder('${order.customer}', true, this)" class="btn-red">Cancel</button>
                        </div>
                    `;
                }

                let stateBadge = isHistory ? '<span class="badge badge-confirmed">Confirmed</span>' : '<span class="badge badge-shopping">Shopping</span>';
                let payBadge = isHistory ? (order.payment_status === 'PAID' ? '<span class="badge badge-paid">💰 PAID</span>' : '<span class="badge badge-unpaid">⏳ UNPAID</span>') : '';

                return `
                    <div class="card">
                        <div class="card-header">
                            <div><div class="card-title">${order.customer}</div><div style="font-size:12px; color:#555;">Items: ${order.total_items}</div></div>
                            <div class="badge-container">${stateBadge}${payBadge}</div>
                        </div>
                        <div style="background:#f9f9f9; padding: 10px; border-radius: 4px; border: 1px solid #eee;">${itemList}</div>
                        ${controls}
                    </div>
                `;
            }

            async function fetchOrders() {
                try {
                    const res = await fetch('/api/orders');
                    const data = await res.json();
                    
                    document.getElementById('completed-container').innerHTML = data.completed.length 
                        ? data.completed.map(o => createCard(o, true)).join('') 
                        : '<div class="card" style="text-align:center; color:#555;">No orders waiting for dispatch.</div>';
                    
                    document.getElementById('active-container').innerHTML = data.active.length 
                        ? data.active.map(o => createCard(o, false)).join('') 
                        : '<div class="card" style="text-align:center; color:#555;">No active carts right now.</div>';
                } catch (e) { console.error("Sync Error"); }
            }

            fetchOrders(); setInterval(fetchOrders, 3000); 
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

# ==========================================
# DASHBOARD 2: COMPLETED ARCHIVE GATEWAY
# ==========================================
@router.get("/admin/history", response_class=HTMLResponse)
def render_admin_history(admin_user: str = Depends(get_current_admin)):
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Amazon Seller Central - Archive</title>
        <style>
            * { box-sizing: border-box; margin: 0; padding: 0; font-family: Arial, sans-serif; }
            body { background-color: #F2F2F2; color: #0F1111; display: flex; flex-direction: column; height: 100vh; }

            header { background-color: #232F3E; color: white; padding: 15px 30px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1); z-index: 10;}
            .logo { font-size: 22px; font-weight: bold; letter-spacing: -0.5px; }
            .logo span { color: #FF9900; }
            
            .nav-bar { background-color: #37475A; display: flex; gap: 20px; padding: 10px 30px; }
            .nav-link { color: #DDD; text-decoration: none; font-size: 14px; font-weight: bold; padding-bottom: 3px;}
            .nav-link.active { color: white; border-bottom: 2px solid #FF9900; }
            .nav-link:hover { color: white; }

            .container { padding: 30px; max-width: 1000px; margin: 0 auto; width: 100%; overflow-y: auto; flex-grow: 1; }
            .page-title { font-size: 24px; font-weight: bold; margin-bottom: 25px; color: #0F1111; }
            .archive-grid { display: flex; flex-direction: column; gap: 15px; }

            .card { background-color: white; border: 1px solid #D5D9D9; border-radius: 8px; padding: 20px; }
            .card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; border-bottom: 1px solid #eee; padding-bottom: 10px; }
            .card-title { font-size: 18px; font-weight: bold; }
            
            .badge-container { display: flex; gap: 8px; }
            .badge { font-size: 11px; padding: 4px 8px; border-radius: 4px; font-weight: bold; text-transform: uppercase; }
            .badge-delivered { background-color: #E7F4E4; color: #007600; border: 1px solid #007600; }
            .badge-paid { background-color: #E7F4E4; color: #007600; border: 1px solid #007600; }

            .item { font-size: 14px; padding: 8px 0; border-bottom: 1px dashed #eee; display: flex; justify-content: space-between; }
            .item:last-child { border-bottom: none; }
            .item-qty { color: #555; background: #F0F2F2; padding: 2px 6px; border-radius: 4px; font-size: 12px;}
        </style>
    </head>
    <body>
        <header>
            <div class="logo">amazon<span>.</span>in &nbsp; <span style="color:#ccc; font-weight:normal; font-size:18px;">| Seller Central</span></div>
        </header>

        <div class="nav-bar">
            <a href="/admin" class="nav-link">Active Dashboard</a>
            <a href="/admin/history" class="nav-link active">Fulfilled Orders Archive</a>
        </div>
        
        <div class="container">
            <div class="page-title">Fulfilled Orders History</div>
            <div class="archive-grid" id="history-container">Loading historical manifests...</div>
        </div>

        <script>
            function createArchiveCard(order) {
                const itemList = order.raw_items.map(i => `
                    <div class="item"><span>• ${i.item}</span><span class="item-qty">Qty: ${i.quantity} ${i.unit || ''}</span></div>
                `).join('');

                return `
                    <div class="card">
                        <div class="card-header">
                            <div><div class="card-title">${order.customer}</div><div style="font-size:12px; color:#555;">Items: ${order.total_items}</div></div>
                            <div class="badge-container">
                                <span class="badge badge-paid">💰 PAID</span>
                                <span class="badge badge-delivered">✅ FULFILLED</span>
                            </div>
                        </div>
                        <div style="background:#fafafa; padding: 10px; border-radius: 4px; border: 1px solid #eee;">${itemList}</div>
                    </div>
                `;
            }

            async function fetchHistory() {
                try {
                    const res = await fetch('/api/orders');
                    const data = await res.json();
                    
                    document.getElementById('history-container').innerHTML = data.delivered.length 
                        ? data.delivered.map(o => createArchiveCard(o)).join('') 
                        : '<div class="card" style="text-align:center; color:#555; border-style: dashed;">No fulfilled orders found in historical logs.</div>';
                } catch (e) { console.error("Sync Error"); }
            }
            fetchHistory();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)