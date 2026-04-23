from flask import Blueprint, request, jsonify
from models.marketplace import (
    add_product,
    get_all_products,
    get_product_by_id,
    update_product,
    delete_product
)


marketplace_bp = Blueprint("marketplace", __name__)


# ===============================
# ADD PRODUCT (ADMIN / USER)
# ===============================
@marketplace_bp.route("/add", methods=["POST"])
def add_marketplace_product():
    data = request.json

    required_fields = [
        "category", "mode", "name", "price",
        "quantity", "description", "username", "role"
    ]

    for field in required_fields:
        if field not in data:
            return jsonify({"message": f"{field} is required"}), 400

    add_product(data)
    return jsonify({"message": "Product added successfully"}), 201


# ===============================
# GET ALL PRODUCTS (PUBLIC)
# ===============================
@marketplace_bp.route("/list", methods=["GET"])
def list_marketplace_products():
    products = get_all_products()

    # Convert ObjectId to string
    for product in products:
        product["_id"] = str(product["_id"])

    return jsonify(products), 200


# ===============================
# UPDATE PRODUCT
# ===============================
@marketplace_bp.route("/update/<product_id>", methods=["PUT"])
def update_marketplace_product(product_id):
    data = request.json
    username = data.get("username")
    role = data.get("role")

    product = get_product_by_id(product_id)

    if not product:
        return jsonify({"message": "Product not found"}), 404

    # Permission check
    if product["added_by"] != username and role != "admin":
        return jsonify({"message": "Unauthorized"}), 403

    update_data = {
        "name": data.get("name"),
        "price": data.get("price"),
        "quantity": data.get("quantity"),
        "description": data.get("description"),
        "mode": data.get("mode")
    }

    # Remove None values
    update_data = {k: v for k, v in update_data.items() if v is not None}

    update_product(product_id, update_data)
    return jsonify({"message": "Product updated successfully"}), 200


# ===============================
# DELETE PRODUCT
# ===============================
@marketplace_bp.route("/delete/<product_id>", methods=["DELETE"])
def delete_marketplace_product(product_id):
    data = request.json
    username = data.get("username")
    role = data.get("role")

    product = get_product_by_id(product_id)

    if not product:
        return jsonify({"message": "Product not found"}), 404

    # Permission check
    if product["added_by"] != username and role != "admin":
        return jsonify({"message": "Unauthorized"}), 403

    delete_product(product_id)
    return jsonify({"message": "Product deleted successfully"}), 200


# ===============================
# GET USER PRODUCTS
# ===============================
@marketplace_bp.route("/my-list", methods=["GET"])
def list_user_products():
    username = request.args.get("username")
    if not username:
        return jsonify({"message": "Username is required"}), 400

    all_products = get_all_products()
    user_products = [p for p in all_products if p.get("added_by") == username]

    # Convert ObjectId to string
    for product in user_products:
        product["_id"] = str(product["_id"])

    return jsonify(user_products), 200
