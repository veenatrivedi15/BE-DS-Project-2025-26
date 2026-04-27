from database.mongo import mongo

def buy_product(name, price):
    mongo.db.buyer_orders.insert_one({
        "product_name": name,
        "price": price
    })
