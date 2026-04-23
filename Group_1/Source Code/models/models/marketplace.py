from database.mongo import mongo
from bson import ObjectId
from datetime import datetime


def add_product(data):
    data["added_by"] = data["username"]
    data["created_at"] = datetime.utcnow()
    mongo.db.marketplace_products.insert_one(data)


def get_all_products():
    return list(mongo.db.marketplace_products.find())


def get_product_by_id(product_id):
    return mongo.db.marketplace_products.find_one({
        "_id": ObjectId(product_id)
    })


def update_product(product_id, update_data):
    mongo.db.marketplace_products.update_one(
        {"_id": ObjectId(product_id)},
        {"$set": update_data}
    )


def delete_product(product_id):
    mongo.db.marketplace_products.delete_one({
        "_id": ObjectId(product_id)
    })
