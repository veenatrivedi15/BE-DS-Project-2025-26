from database.mongo import mongo
from bson import ObjectId
from datetime import datetime


def create_order(product_id, buyer, quantity):

    product = mongo.db.marketplace_products.find_one({
        "_id": ObjectId(product_id)
    })

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
        "product_id": product_id,
        "buyer": buyer,
        "seller": product["added_by"],
        "price": product["price"],
        "quantity": quantity,
        "order_date": datetime.utcnow()
    })

    return True, "Order successful"
