import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
CORS(app)

raw_url = os.environ.get('DATABASE_URL', '').strip()
if raw_url.startswith('postgres://'):
    DATABASE_URL = raw_url.replace('postgres://', 'postgresql://', 1)
else:
    DATABASE_URL = raw_url

def get_db():
    return psycopg2.connect(DATABASE_URL, sslmode='require')

def init_db():
    if not DATABASE_URL:
        return
    try:
        conn = get_db()
        cur = conn.cursor()
        
        # 1. సెల్లర్స్ టేబుల్
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
        
        # 2. బయ్యర్స్ టేబుల్
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

        # 3. ప్రొడక్ట్స్ టేబుల్
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

        # 4. ఆర్డర్స్ టేబుల్ (అమ్మకాలు, 2% కమీషన్ ట్రాకింగ్)
        cur.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                product_id INT REFERENCES products(id),
                seller_id INT REFERENCES sellers(id),
                buyer_name VARCHAR(255),
                buyer_phone VARCHAR(20),
                buyer_address TEXT,
                amount NUMERIC NOT NULL,
                admin_fee NUMERIC NOT NULL,
                seller_payout NUMERIC NOT NULL,
                payment_mode VARCHAR(50),
                status VARCHAR(50) DEFAULT 'Delivered',
                order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')

        # 5. రిటర్న్స్ & రీఫండ్స్ టేబుల్
        cur.execute('''
            CREATE TABLE IF NOT EXISTS returns (
                id SERIAL PRIMARY KEY,
                order_id INT REFERENCES orders(id),
                seller_id INT REFERENCES sellers(id),
                reason TEXT NOT NULL,
                refund_amount NUMERIC NOT NULL,
                status VARCHAR(50) DEFAULT 'Pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')

        conn.commit()
        cur.close()
        conn.close()
        print("All PostgreSQL tables initialized securely!")
    except Exception as e:
        print("DB Init Error:", e)

init_db()

@app.route('/', methods=['GET'])
def home():
    return "MeeStore Backend is Running Live & Secure!", 200

# ----- సెల్లర్ ఆథెంటికేషన్ (లాగిన్ & రిజిస్టర్) -----
@app.route('/api/seller/register', methods=['POST'])
def seller_register():
    try:
        data = request.get_json(force=True)
        shop_name = data.get('shop_name')
        phone = data.get('phone')
        upi_id = data.get('upi_id')
        password = data.get('password')

        hashed_pw = generate_password_hash(password)
        conn = get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('''
            INSERT INTO sellers (shop_name, phone, upi_id, password_hash)
            VALUES (%s, %s, %s, %s) RETURNING id, shop_name, phone, upi_id;
        ''', (shop_name, phone, upi_id, hashed_pw))
        seller = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        return jsonify(seller), 201
    except Exception as e:
        return jsonify({"error": "మొబైల్ నంబర్ ఇప్పటికే రిజిస్టర్ అయి ఉండవచ్చు"}), 400

@app.route('/api/seller/login', methods=['POST'])
def seller_login():
    try:
        data = request.get_json(force=True)
        phone = data.get('phone')
        password = data.get('password')

        conn = get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('SELECT * FROM sellers WHERE phone = %s;', (phone,))
        seller = cur.fetchone()
        cur.close()
        conn.close()

        if seller and check_password_hash(seller['password_hash'], password):
            del seller['password_hash']
            return jsonify(seller), 200
        return jsonify({"error": "ఫోన్ నంబర్ లేదా పాస్‌వర్డ్ తప్పు"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ----- ప్రొడక్ట్ మేనేజ్‌మెంట్ -----
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

@app.route('/api/products', methods=['POST'])
def add_product():
    try:
        data = request.get_json(force=True)
        seller_id = data.get('seller_id')
        name = data.get('name')
        category = data.get('category')
        mrp = data.get('mrp')
        price = float(data.get('price'))
        stock = int(data.get('stock', 10))
        image_url = data.get('image_url')
        seller_phone = data.get('seller_phone')
        seller_upi = data.get('seller_upi')

        conn = get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('''
            INSERT INTO products (seller_id, name, category, mrp, price, stock, image_url, seller_phone, seller_upi)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING *;
        ''', (seller_id, name, category, mrp, price, stock, image_url, seller_phone, seller_upi))
        item = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        return jsonify(item), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ----- సెల్లర్ డ్యాష్‌బోర్డ్ డేటా (స్టాక్ & సేల్స్ లెక్కలు) -----
@app.route('/api/seller/dashboard/<int:seller_id>', methods=['GET'])
def seller_dashboard(seller_id):
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('SELECT * FROM products WHERE seller_id = %s ORDER BY id DESC;', (seller_id,))
        products = cur.fetchall()

        cur.execute('SELECT * FROM orders WHERE seller_id = %s ORDER BY id DESC;', (seller_id,))
        orders = cur.fetchall()

        cur.execute('SELECT * FROM returns WHERE seller_id = %s ORDER BY id DESC;', (seller_id,))
        returns = cur.fetchall()

        total_sales = sum(float(o['seller_payout']) for o in orders if o['status'] == 'Delivered')
        cur.close()
        conn.close()

        return jsonify({
            "products": products,
            "orders": orders,
            "returns": returns,
            "total_payout": total_sales
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ----- అడ్మిన్ రిపోర్ట్ (మీ 2% ఆదాయం, టెక్నికల్ లాస్) -----
@app.route('/api/admin/report', methods=['GET'])
def admin_report():
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute('SELECT COUNT(*) as total_sellers FROM sellers;')
        total_sellers = cur.fetchone()['total_sellers']

        cur.execute('SELECT COUNT(*) as total_orders, COALESCE(SUM(amount), 0) as gross_turnover, COALESCE(SUM(admin_fee), 0) as total_admin_earnings FROM orders WHERE status = "Delivered";')
        sales_summary = cur.fetchone()

        cur.execute('SELECT COUNT(*) as total_returns, COALESCE(SUM(refund_amount), 0) as total_loss FROM returns;')
        returns_summary = cur.fetchone()

        cur.close()
        conn.close()

        return jsonify({
            "total_sellers": total_sellers,
            "gross_turnover": float(sales_summary['gross_turnover']),
            "admin_income_2_percent": float(sales_summary['total_admin_earnings']),
            "technical_returns_loss": float(returns_summary['total_loss']),
            "completed_orders": sales_summary['total_orders']
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
    
