import os
import sqlite3
from flask import Flask, request, jsonify
from flask_cors import CORS
import razorpay

app = Flask(__name__)
# వేర్వేరు డొమైన్ల (GitHub Pages) నుండి రిక్వెస్ట్‌లను అనుమతించడానికి CORS
CORS(app)

DB_NAME = "meestore.db"

# Razorpay టెస్ట్ కీలు (మీ వద్ద ఉన్నప్పుడు ఎన్విరాన్‌మెంట్‌లో మార్చుకోవచ్చు)
RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID", "rzp_test_placeholder")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "secret_placeholder")
client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

# ----------------- 1. డేటాబేస్ టేబుల్స్ తయారీ -----------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # ప్రొడక్ట్స్ పట్టిక
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL,
            mrp REAL NOT NULL,
            stock INTEGER DEFAULT 0,
            weight INTEGER DEFAULT 500,
            image TEXT NOT NULL,
            description TEXT,
            seller_id TEXT DEFAULT 'DEFAULT_SELLER'
        )
    ''')
    
    # ఆర్డర్లు & కమిషన్ పట్టిక
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT,
            customer_phone TEXT,
            customer_address TEXT,
            total_amount REAL,
            commission_amount REAL,
            seller_payout REAL,
            order_status TEXT DEFAULT 'PENDING',
            razorpay_order_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

# ----------------- 2. API ENDPOINTS -----------------

@app.route('/', methods=['GET'])
def home():
    return jsonify({"status": "live", "message": "MeeStore Cloud API విజయవంతంగా నడుస్తోంది!"}), 200

# ప్రొడక్ట్స్ ఫెచ్ చేయడం (కస్టమర్ హోమ్‌పేజీ కోసం)
@app.route('/api/products', methods=['GET'])
def get_products():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, category, price, mrp, stock, weight, image, description FROM products ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    
    products = []
    for r in rows:
        products.append({
            "id": r[0], "title": r[1], "category": r[2],
            "price": r[3], "mrp": r[4], "stock": r[5],
            "weight": r[6], "image": r[7], "desc": r[8]
        })
    return jsonify(products), 200

# కొత్త ప్రొడక్ట్ జోడించడం (సెల్లర్ పోర్టల్ నుండి)
@app.route('/api/products', methods=['POST'])
def add_product():
    data = request.json
    title = data.get("title")
    category = data.get("category")
    price = float(data.get("price", 0))
    mrp = float(data.get("mrp", 0))
    stock = int(data.get("stock", 1))
    weight = int(data.get("weight", 500))
    image = data.get("image")
    description = data.get("desc", "")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO products (title, category, price, mrp, stock, weight, image, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (title, category, price, mrp, stock, weight, image, description))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()

    return jsonify({"status": "success", "product_id": new_id, "message": "ప్రొడక్ట్ సేవ్ అయింది"}), 201

# ఆర్డర్ సృష్టించడం & కమిషన్ లెక్కించడం
@app.route('/api/create-order', methods=['POST'])
def create_order():
    data = request.json
    total_amount = float(data.get("total_amount", 0))
    
    # 10% ప్లాట్‌ఫామ్ కమిషన్
    commission = round(total_amount * 0.10, 2)
    seller_payout = round(total_amount - commission, 2)

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO orders (customer_name, customer_phone, customer_address, total_amount, commission_amount, seller_payout)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        data.get("customer_name"),
        data.get("customer_phone"),
        data.get("customer_address"),
        total_amount,
        commission,
        seller_payout
    ))
    conn.commit()
    order_id = cursor.lastrowid
    conn.close()

    return jsonify({
        "status": "success",
        "order_id": order_id,
        "total": total_amount,
        "commission": commission,
        "seller_payout": seller_payout
    }), 201
    
# ఉత్పత్తి వివరాలను అప్‌డేట్ చేయడం (Update Product)
@app.route('/api/products/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    data = request.json
    title = data.get("title")
    category = data.get("category")
    price = float(data.get("price", 0))
    mrp = float(data.get("mrp", 0))
    stock = int(data.get("stock", 0))
    weight = int(data.get("weight", 500))
    image = data.get("image")
    description = data.get("desc", "")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE products 
        SET title = ?, category = ?, price = ?, mrp = ?, stock = ?, weight = ?, image = ?, description = ?
        WHERE id = ?
    ''', (title, category, price, mrp, stock, weight, image, description, product_id))
    conn.commit()
    conn.close()

    return jsonify({"status": "success", "message": "ఉత్పత్తి విజయవంతంగా అప్‌డేట్ చేయబడింది!"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
  
