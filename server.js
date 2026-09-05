const express = require('express');
const cors = require('cors');
const { Pool } = require('pg');

const app = express();
app.use(cors());
app.use(express.json());

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: { rejectUnauthorized: false }
});

// టేబుల్ లేకపోతే ఆటోమేటిక్‌గా క్రియేట్ చేస్తుంది (seller_upi తో సహా)
async function initDB() {
  try {
    await pool.query(`
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
    `);
    // పాత టేబుల్ ఉంటే seller_upi కాలమ్ ను యాడ్ చేస్తుంది
    await pool.query(`
      ALTER TABLE products ADD COLUMN IF NOT EXISTS seller_upi VARCHAR(100);
    `);
    console.log("Database & Table Ready!");
  } catch (err) {
    console.error("DB Init Error:", err);
  }
}
initDB();

// అన్ని ప్రొడక్ట్స్ తెచ్చే API
app.get('/api/products', async (req, res) => {
  try {
    const result = await pool.query('SELECT * FROM products ORDER BY id DESC');
    res.json(result.rows);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// కొత్త ప్రొడక్ట్ యాడ్ చేసే API
app.post('/api/products', async (req, res) => {
  try {
    const { name, category, mrp, price, image_url, seller_phone, seller_upi } = req.body;
    const result = await pool.query(
      `INSERT INTO products (name, category, mrp, price, image_url, seller_phone, seller_upi) 
       VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING *`,
      [name, category, mrp, price, image_url, seller_phone, seller_upi]
    );
    res.status(201).json(result.rows[0]);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
