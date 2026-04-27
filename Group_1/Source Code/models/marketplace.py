from database.mongo import mongo
from bson.objectid import ObjectId
from datetime import datetime

# ===============================
# PRODUCT MANAGEMENT
# ===============================

def add_product(data, images=None):
    product = {
        "category": data.get("category"),      # crop | fertilizer | equipment
        "mode": data.get("mode"),              # sell | rent
        "name": data.get("name"),
        "price": data.get("price"),
        "quantity": data.get("quantity"),
        "description": data.get("description"),
        "added_by": data.get("username"),
        "role": data.get("role"),              # admin | user
        "images": images if images is not None else [],
        "created_at": datetime.utcnow()
    }

    result = mongo.db.marketplace_products.insert_one(product)
    return result.inserted_id

def get_all_products():
    return list(mongo.db.marketplace_products.find())

def get_product_by_id(product_id):
    try:
        return mongo.db.marketplace_products.find_one({
            "_id": ObjectId(product_id)
        })
    except:
        return None

def update_product(product_id, update_data):
    try:
        mongo.db.marketplace_products.update_one(
            {"_id": ObjectId(product_id)},
            {"$set": update_data}
        )
        return True
    except:
        return False

def delete_product(product_id):
    try:
        mongo.db.marketplace_products.delete_one({
            "_id": ObjectId(product_id)
        })
        return True
    except:
        return False

# ===============================
# ORDER MANAGEMENT
# ===============================

def create_order(product_id, buyer, quantity):
    try:
        product = get_product_by_id(product_id)

        if not product:
            return False, "Product not found"

        if product["quantity"] < quantity:
            return False, "Not enough stock"

        # Reduce stock
        mongo.db.marketplace_products.update_one(
            {"_id": ObjectId(product_id)},
            {"$inc": {"quantity": -quantity}}
        )

        # Save order
        mongo.db.marketplace_orders.insert_one({
            "product_id": str(product_id),
            "buyer": buyer,
            "seller": product["added_by"],
            "price": product["price"],
            "quantity": quantity,
            "order_date": datetime.utcnow()
        })

        return True, "Order successful"
    except Exception as e:
        return False, str(e)
