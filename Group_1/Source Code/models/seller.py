from database.mongo import mongo

def add_product(name, price, photo, description):
    mongo.db.seller_products.insert_one({
        "product_name": name,
        "product_price": price,
        "product_photo": photo,
        "product_description": description
    })
