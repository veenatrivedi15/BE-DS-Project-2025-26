from flask import Blueprint, request, jsonify
from models.ecommerce import add_seller_product, buy_product

ecommerce_bp = Blueprint("ecommerce", __name__)

@ecommerce_bp.route("/add-product", methods=["POST"])
def add_seller_product():
    data = request.json
    add_product(
        data["product_name"],
        data["product_price"],
        data["product_photo"],
        data["product_description"]
    )
    return jsonify({"message": "Product added successfully"})

@ecommerce_bp.route("/buy-product", methods=["POST"])
def buyer_purchase():
    data = request.json
    buy_product(data["product_name"], data["price"])
    return jsonify({"message": "Product purchased successfully"})
