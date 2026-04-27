from database.mongo import mongo
from datetime import datetime

# ===============================
# SELLER LOGIC
# ===============================

def add_seller_product(name, price, photo, description):
    mongo.db.seller_products.insert_one({
        "product_name": name,
        "product_price": price,
        "product_photo": photo,
        "product_description": description,
        "created_at": datetime.utcnow()
    })

# ===============================
# BUYER LOGIC
# ===============================

def buy_product(name, price):
    mongo.db.buyer_orders.insert_one({
        "product_name": name,
        "price": price,
        "order_date": datetime.utcnow()
    })
