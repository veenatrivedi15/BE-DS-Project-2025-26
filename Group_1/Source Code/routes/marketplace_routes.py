from flask import Blueprint, request, jsonify
import os
import uuid
from werkzeug.utils import secure_filename
from models.marketplace import (
    add_product,
    get_all_products,
    get_product_by_id,
    update_product,
    delete_product,
    create_order
)

marketplace_bp = Blueprint("marketplace", __name__)

# ===============================
# ADD PRODUCT
# ===============================
@marketplace_bp.route("/add", methods=["POST"])
def add_marketplace_product():
    data = request.form.to_dict() if request.form else request.json
    if not data:
        return jsonify({"message": "No data provided"}), 400

    required_fields = ["category", "mode", "name", "price", "quantity", "description", "username", "role"]

    for field in required_fields:
        if field not in data:
            return jsonify({"message": f"{field} is required"}), 400

    try:
        data["price"] = int(data["price"])
    except (ValueError, TypeError):
        pass

    images = []
    if 'productImages' in request.files:
        files = request.files.getlist('productImages')
        if len(files) < 1 or len(files) > 3:
            return jsonify({"message": "Please upload between 1 and 3 images"}), 400
        
        upload_dir = os.path.join(os.getcwd(), 'static', 'uploads', 'products')
        os.makedirs(upload_dir, exist_ok=True)
        
        for file in files:
            if file and file.filename:
                ext = os.path.splitext(file.filename)[1]
                filename = secure_filename(f"{uuid.uuid4().hex}{ext}")
                file_path = os.path.join(upload_dir, filename)
                file.save(file_path)
                images.append(f"uploads/products/{filename}")
    else:
        return jsonify({"message": "At least 1 image is required"}), 400

    add_product(data, images)
    return jsonify({"message": "Product added successfully"}), 201

# ===============================
# LIST ALL PRODUCTS
# ===============================
@marketplace_bp.route("/list", methods=["GET"])
def list_marketplace_products():
    products = get_all_products()
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

    if product["added_by"] != username and role != "admin":
        return jsonify({"message": "Unauthorized"}), 403

    update_data = {
        "name": data.get("name"),
        "price": data.get("price"),
        "quantity": data.get("quantity"),
        "description": data.get("description"),
        "mode": data.get("mode")
    }
    update_data = {k: v for k, v in update_data.items() if v is not None}

    if update_product(product_id, update_data):
        return jsonify({"message": "Product updated successfully"}), 200
    return jsonify({"message": "Update failed"}), 500

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

    if product["added_by"] != username and role != "admin":
        return jsonify({"message": "Unauthorized"}), 403

    if delete_product(product_id):
        return jsonify({"message": "Product deleted successfully"}), 200
    return jsonify({"message": "Delete failed"}), 500

# ===============================
# PLACE ORDER
# ===============================
@marketplace_bp.route("/order", methods=["POST"])
def place_order():
    data = request.json
    product_id = data.get("product_id")
    buyer = data.get("username")
    quantity = data.get("quantity", 1)

    if not product_id or not buyer:
        return jsonify({"message": "Missing info"}), 400

    success, message = create_order(product_id, buyer, quantity)
    if success:
        return jsonify({"message": message}), 200
    return jsonify({"message": message}), 400

# ===============================
# MY LISTINGS
# ===============================
@marketplace_bp.route("/my-list", methods=["GET"])
def list_user_products():
    username = request.args.get("username")
    if not username:
        return jsonify({"message": "Username is required"}), 400

    all_products = get_all_products()
    user_products = [p for p in all_products if p.get("added_by") == username]
    for product in user_products:
        product["_id"] = str(product["_id"])

    return jsonify(user_products), 200
