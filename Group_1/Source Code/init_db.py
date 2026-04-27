from app import app
from database.mongo import mongo

def init_db():
    print("Initializing Database...")
    with app.app_context():
        # 1. Access the database
        db = mongo.db
        
        # --- USER/ORG AUTH COLLECTIONS ---
        print("Checking 'user_signup' collection...")
        if 'user_signup' not in db.list_collection_names():
            print("user_signup does not exist. It will be created on first insert.")
        else:
            print("user_signup exists.")
        db.user_signup.create_index("username", unique=True)
        print("✅ Unique index created on user_signup.username")

        print("Checking 'organizations' collection...")
        if 'organizations' not in db.list_collection_names():
            print("organizations does not exist. It will be created on first insert.")
        else:
            print("organizations exists.")
        db.organizations.create_index("username", unique=True)
        print("✅ Unique index created on organizations.username")

        # --- MARKETPLACE COLLECTIONS ---
        print("Checking 'marketplace_products' collection...")
        if 'marketplace_products' not in db.list_collection_names():
            print("Collection does not exist. Creating via index creation...")
        else:
            print("Collection exists.")

        # 3. Create Indexes (This ensures collection exists & makes queries fast)
        # We query by 'added_by' (username) for the dashboard
        db.marketplace_products.create_index("added_by")
        print("✅ Index created on 'added_by'")
        
        # We query by 'category' and 'mode' for the main market
        db.marketplace_products.create_index("category")
        db.marketplace_products.create_index("mode")
        print("✅ Indexes created on 'category' and 'mode'")

        # optionally ensure order collection is available
        print("Checking 'marketplace_orders' collection...")
        if 'marketplace_orders' not in db.list_collection_names():
            print("marketplace_orders does not exist. It will be created on first insert.")
        else:
            print("marketplace_orders exists.")
        # index by product_id and buyer for quick lookup
        db.marketplace_orders.create_index("product_id")
        db.marketplace_orders.create_index("buyer")
        print("✅ Indexes created on marketplace_orders.product_id and buyer")

        # --- LOGGING COLLECTIONS ---
        for col in ['user_login', 'admin_login', 'admin_login_log']:
            print(f"Checking '{col}' collection...")
            if col not in db.list_collection_names():
                print(f"{col} does not exist. It will be created on first insert.")
            else:
                print(f"{col} exists.")
            # create a basic index on username for each
            db[col].create_index("username")
            print(f"✅ Index created on {col}.username")

        # 4. (Optional) Inspect counts for sanity
        counts = {
            'user_signup': db.user_signup.count_documents({}),
            'marketplace_products': db.marketplace_products.count_documents({}),
            'marketplace_orders': db.marketplace_orders.count_documents({})
        }
        for name, c in counts.items():
            print(f"Collection '{name}' has {c} documents.")

    print("\nDatabase Initialization Complete! 🚀")

    print("\nDatabase Initialization Complete! 🚀")

if __name__ == "__main__":
    init_db()
