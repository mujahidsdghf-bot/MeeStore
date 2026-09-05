import os
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Render లో ఇచ్చిన PostgreSQL DATABASE_URL
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, sslmode='require')

# డేటాబేస్ టేబుల్ సిద్ధం చేయడం
def init_db():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                category VARCHAR(100),
                mrp NUMERIC,
                price NUMERIC NOT NULL,
                image_url TEXT,
                seller_phone VARCHAR(20),
                seller_upi VARCHAR(100)
            );
        ''')
        # పాత టేబుల్ ఉంటే seller_upi కాలమ్ ను యాడ్ చేస్తుంది
        cur.execute('''
            ALTER TABLE products ADD COLUMN IF NOT EXISTS seller_upi VARCHAR(100);
        ''')
        conn.commit()
        cur.close()
        conn.close()
        print("PostgreSQL Database Initialized Successfully!")
    except Exception as e:
        print(f"Database Init Error: {e}")

# యాప్ స్టార్ట్ అయ్యేటప్పుడు టేబుల్ క్రియేట్ అవుతుంది
init_db()

# 1. అన్ని ఉత్పత్తులను తెచ్చే API
@app.route('/api/products', methods=['GET'])
def get_products():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('SELECT * FROM products ORDER BY id DESC;')
        products = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(products), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 2. కొత్త ఉత్పత్తిని జోడించే API
@app.route('/api/products', methods=['POST'])
def add_product():
    try:
        data = request.json
        name = data.get('name')
        category = data.get('category')
        mrp = data.get('mrp')
        price = data.get('price')
        image_url = data.get('image_url')
        seller_phone = data.get('seller_phone')
        seller_upi = data.get('seller_upi')

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('''
            INSERT INTO products (name, category, mrp, price, image_url, seller_phone, seller_upi)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING *;
        ''', (name, category, mrp, price, image_url, seller_phone, seller_upi))
        
        new_prod = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        return jsonify(new_prod), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
