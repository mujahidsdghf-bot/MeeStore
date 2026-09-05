import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
CORS(app)

raw_url = os.environ.get('DATABASE_URL', '').strip()
DATABASE_URL = raw_url.replace('postgres://', 'postgresql://', 1) if raw_url.startswith('postgres://') else raw_url

def get_db():
    return psycopg2.connect(DATABASE_URL, sslmode='require')

def init_db():
    if not DATABASE_URL:
        return
    try:
        conn = get_db()
        cur = conn.cursor()
        
        # Sellers
        cur.execute('''
            CREATE TABLE IF NOT EXISTS sellers (
                id SERIAL PRIMARY KEY,
                shop_name VARCHAR(255) NOT NULL,
                phone VARCHAR(20) UNIQUE NOT NULL,
                upi_id VARCHAR(100) NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        
        # Buyers (బయ్యర్స్ టేబుల్)
        cur.execute('''
            CREATE TABLE IF NOT EXISTS buyers (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                phone VARCHAR(20) UNIQUE NOT NULL,
                address TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')

        # Products
        cur.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id SERIAL PRIMARY KEY,
                seller_id INT REFERENCES sellers(id) ON DELETE CASCADE,
                name VARCHAR(255) NOT NULL,
                category VARCHAR(100),
                mrp NUMERIC,
                price NUMERIC NOT NULL,
                stock INT DEFAULT 10,
                image_url TEXT,
                seller_phone VARCHAR(20),
                seller_upi VARCHAR(100)
            );
        ''')

        # Orders (సేల్స్, 2% కమీషన్ ట్రాకింగ్)
        cur.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                buyer_id INT REFERENCES buyers(id),
                seller_id INT REFERENCES sellers(id),
                product_name VARCHAR(255) NOT NULL,
                amount NUMERIC NOT NULL,
                admin_fee NUMERIC NOT NULL,
                seller_payout NUMERIC NOT NULL,
                buyer_name VARCHAR(255),
                buyer_phone VARCHAR(20),
                buyer_address TEXT,
                payment_mode VARCHAR(50),
                status VARCHAR(50) DEFAULT 'Placed',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')

        # Returns (రిటర్న్స్ & రీఫండ్స్)
        cur.execute('''
            CREATE TABLE IF NOT EXISTS returns (
                id SERIAL PRIMARY KEY,
                order_id INT REFERENCES orders(id),
                seller_id INT REFERENCES sellers(id),
                buyer_id INT REFERENCES buyers(id),
                reason TEXT NOT NULL,
                refund_amount NUMERIC NOT NULL,
                status VARCHAR(50) DEFAULT 'Requested',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')

        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print("DB Init Error:", e)

init_db()

@app.route('/', methods=['GET'])
def home():
    return "MeeStore Backend is Running Live & Secure!", 200

# ----- బయ్యర్ ఆథెంటికేషన్ -----
@app.route('/api/buyer/register', methods=['POST'])
def buyer_register():
    try:
        data = request.get_json(force=True)
        pwd_hash = generate_password_hash(data['password'])
        conn = get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('''
            INSERT INTO buyers (name, phone, address, password_hash)
            VALUES (%s, %s, %s, %s) RETURNING id, name, phone, address;
        ''', (data['name'], data['phone'], data['address'], pwd_hash))
        buyer = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        return jsonify(buyer), 201
    except Exception:
        return jsonify({"error": "ఈ మొబైల్ నంబర్ ఇప్పటికే రిజిస్టర్ అయింది"}), 400

@app.route('/api/buyer/login', methods=['POST'])
def buyer_login():
    try:
        data = request.get_json(force=True)
        conn = get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('SELECT * FROM buyers WHERE phone = %s;', (data['phone'],))
        buyer = cur.fetchone()
        cur.close()
        conn.close()

        if buyer and check_password_hash(buyer['password_hash'], data['password']):
            del buyer['password_hash']
            return jsonify(buyer), 200
        return jsonify({"error": "మొబైల్ నంబర్ లేదా పాస్‌వర్డ్ తప్పు"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ----- సెల్లర్ ఆథెంటికేషన్ -----
@app.route('/api/seller/register', methods=['POST'])
def seller_register():
    try:
        data = request.get_json(force=True)
        pwd_hash = generate_password_hash(data['password'])
        conn = get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('''
            INSERT INTO sellers (shop_name, phone, upi_id, password_hash)
            VALUES (%s, %s, %s, %s) RETURNING id, shop_name, phone, upi_id;
        ''', (data['shop_name'], data['phone'], data['upi_id'], pwd_hash))
        seller = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        return jsonify(seller), 201
    except Exception:
        return jsonify({"error": "ఈ నంబర్ ఇప్పటికే రిజిస్టర్ అయింది"}), 400

@app.route('/api/seller/login', methods=['POST'])
def seller_login():
    try:
        data = request.get_json(force=True)
        conn = get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('SELECT * FROM sellers WHERE phone = %s;', (data['phone'],))
        seller = cur.fetchone()
        cur.close()
        conn.close()

        if seller and check_password_hash(seller['password_hash'], data['password']):
            del seller['password_hash']
            return jsonify(seller), 200
        return jsonify({"error": "మొబైల్ లేదా పాస్‌వర్డ్ తప్పు"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ----- ప్రొడక్ట్స్ -----
@app.route('/api/products', methods=['GET'])
def get_products():
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute('SELECT * FROM products ORDER BY id DESC;')
    items = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(items), 200

@app.route('/api/products', methods=['POST'])
def add_product():
    data = request.get_json(force=True)
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute('''
        INSERT INTO products (seller_id, name, category, mrp, price, stock, image_url, seller_phone, seller_upi)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING *;
    ''', (data.get('seller_id'), data['name'], data.get('category'), data.get('mrp'), data['price'], data.get('stock', 10), data['image_url'], data.get('seller_phone'), data.get('seller_upi')))
    p = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return jsonify(p), 201

# ----- ఆర్డర్ ప్లేస్‌మెంట్ (2% ఫీజు కాలిక్యులేషన్) -----
@app.route('/api/orders/place', methods=['POST'])
def place_order():
    try:
        data = request.get_json(force=True)
        amt = float(data['amount'])
        admin_fee = round(amt * 0.02, 2)  # 2% ప్లాట్‌ఫామ్ ఫీజు
        seller_payout = round(amt - admin_fee, 2)

        conn = get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('''
            INSERT INTO orders (buyer_id, seller_id, product_name, amount, admin_fee, seller_payout, buyer_name, buyer_phone, buyer_address, payment_mode)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING *;
        ''', (data.get('buyer_id'), data.get('seller_id'), data['product_name'], amt, admin_fee, seller_payout, data['buyer_name'], data['buyer_phone'], data['buyer_address'], data['payment_mode']))
        order = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        return jsonify(order), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ----- బయ్యర్ డ్యాష్‌బోర్డ్ (మై ఆర్డర్స్) -----
@app.route('/api/buyer/orders/<int:buyer_id>', methods=['GET'])
def buyer_orders(buyer_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute('SELECT * FROM orders WHERE buyer_id = %s ORDER BY id DESC;', (buyer_id,))
    orders = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(orders), 200

# ----- రిటర్న్ / రీఫండ్ రిక్వెస్ట్ -----
@app.route('/api/orders/return', methods=['POST'])
def return_order():
    try:
        data = request.get_json(force=True)
        conn = get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('''
            INSERT INTO returns (order_id, seller_id, buyer_id, reason, refund_amount)
            VALUES (%s, %s, %s, %s, %s) RETURNING *;
        ''', (data['order_id'], data.get('seller_id'), data['buyer_id'], data['reason'], data['refund_amount']))
        cur.execute('UPDATE orders SET status = %s WHERE id = %s;', ('Return Requested', data['order_id']))
        ret = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        return jsonify(ret), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ----- సెల్లర్ డ్యాష్‌బోర్డ్ రిపోర్ట్ -----
@app.route('/api/seller/dashboard/<int:seller_id>', methods=['GET'])
def seller_dashboard(seller_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute('SELECT * FROM products WHERE seller_id = %s ORDER BY id DESC;', (seller_id,))
    prods = cur.fetchall()
    cur.execute('SELECT * FROM orders WHERE seller_id = %s ORDER BY id DESC;', (seller_id,))
    orders = cur.fetchall()
    cur.execute('SELECT * FROM returns WHERE seller_id = %s ORDER BY id DESC;', (seller_id,))
    returns = cur.fetchall()
    cur.close()
    conn.close()

    total_net = sum(float(o['seller_payout']) for o in orders if o['status'] != 'Cancelled')
    return jsonify({
        "products": prods,
        "orders": orders,
        "returns": returns,
        "total_payout": round(total_net, 2)
    }), 200

# ----- అడ్మిన్ రిపోర్ట్ -----
@app.route('/api/admin/report', methods=['GET'])
def admin_report():
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute('SELECT COUNT(*) as sellers FROM sellers;')
    sellers_cnt = cur.fetchone()['sellers']
    cur.execute('SELECT COUNT(*) as buyers FROM buyers;')
    buyers_cnt = cur.fetchone()['buyers']
    cur.execute('SELECT COALESCE(SUM(amount),0) as turnover, COALESCE(SUM(admin_fee),0) as earnings FROM orders;')
    sales = cur.fetchone()
    cur.execute('SELECT COALESCE(SUM(refund_amount),0) as loss FROM returns;')
    loss = cur.fetchone()['loss']
    cur.close()
    conn.close()

    return jsonify({
        "total_sellers": sellers_cnt,
        "total_buyers": buyers_cnt,
        "gross_turnover": float(sales['turnover']),
        "admin_earnings": float(sales['earnings']),
        "technical_loss": float(loss)
    }), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
        
