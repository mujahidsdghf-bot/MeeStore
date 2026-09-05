import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)
CORS(app)

# Render PostgreSQL URL ని సరిదిద్దడం (postgres:// ని postgresql:// గా మారుస్తుంది)
raw_url = os.environ.get('DATABASE_URL', '')
if raw_url.startswith('postgres://'):
    DATABASE_URL = raw_url.replace('postgres://', 'postgresql://', 1)
else:
    DATABASE_URL = raw_url

def get_db():
    return psycopg2.connect(DATABASE_URL, sslmode='require')

# డేటాబేస్ టేబుల్ మరియు seller_upi కాలమ్ సిద్ధం చేయడం
def init_db():
    if not DATABASE_URL:
        print("DATABASE_URL కనుగొనబడలేదు!")
        return
    try:
        conn = get_db()
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
        print("PostgreSQL Database Ready!")
    except Exception as e:
        print("DB Init Error:", e)

# సర్వర్ స్టార్ట్ అవ్వగానే టేబుల్ క్రియేట్ అవుతుంది
init_db()

@app.route('/', methods=['GET'])
def home():
    return "MeeStore Backend is Running Live!", 200

# 1. ప్రొడక్ట్స్ లిస్ట్ తెచ్చే API
@app.route('/api/products', methods=['GET'])
def get_products():
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('SELECT * FROM products ORDER BY id DESC;')
        items = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(items), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 2. కొత్త ప్రొడక్ట్ యాడ్ చేసే API
@app.route('/api/products', methods=['POST'])
def add_product():
    try:
        data = request.get_json(force=True)
        name = data.get('name')
        category = data.get('category')
        mrp = data.get('mrp')
        price = data.get('price')
        image_url = data.get('image_url')
        seller_phone = data.get('seller_phone')
        seller_upi = data.get('seller_upi')

        conn = get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('''
            INSERT INTO products (name, category, mrp, price, image_url, seller_phone, seller_upi)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING *;
        ''', (name, category, mrp, price, image_url, seller_phone, seller_upi))
        
        saved_item = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        return jsonify(saved_item), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
