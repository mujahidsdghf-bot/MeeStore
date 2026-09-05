import os
import sqlite3
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DB_NAME = "meestore.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # seller_phone ఫీల్డ్‌తో ప్రోడక్ట్స్ టేబుల్
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
            seller_phone TEXT DEFAULT '919999999999'
        )
    ''')
    # ఆర్డర్స్ టేబుల్ (పేమెంట్ మోడ్ మరియు అడ్రస్‌తో)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT,
            customer_phone TEXT,
            customer_address TEXT,
            payment_mode TEXT,
            total_amount REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route('/', methods=['GET'])
def home():
    return jsonify({"status": "live", "message": "MeeStore API Active"}), 200

@app.route('/api/products', methods=['GET'])
def get_products():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, category, price, mrp, stock, weight, image, description, seller_phone FROM products ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    
    products = []
    for r in rows:
        products.append({
            "id": r[0], "title": r[1], "category": r[2],
            "price": r[3], "mrp": r[4], "stock": r[5],
            "weight": r[6], "image": r[7], "desc": r[8],
            "seller_phone": r[9] if len(r) > 9 and r[9] else "919999999999"
        })
    return jsonify(products), 200

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
    desc = data.get("desc", "")
    seller_phone = data.get("seller_phone", "919999999999")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO products (title, category, price, mrp, stock, weight, image, description, seller_phone)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (title, category, price, mrp, stock, weight, image, desc, seller_phone))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()

    return jsonify({"status": "success", "product_id": new_id}), 201

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
    
