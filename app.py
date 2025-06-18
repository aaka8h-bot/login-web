# app.py
import os
import json
import requests
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file, abort

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['SESSION_TYPE'] = 'filesystem'

# Files
USERS_FILE = 'users.json'
PRODUCTS_FILE = 'products.json'
ADMIN_PASSWORD = "admin123"  # Hardcoded admin password

# Initialize files
def init_files():
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'w') as f:
            json.dump([], f)
    
    if not os.path.exists(PRODUCTS_FILE):
        default_products = [
            {"id": 1, "name": "Premium Watch", "price": 299.99, "image": "https://images.unsplash.com/photo-1523275335684-37898b6baf30", "description": "Luxury automatic watch with sapphire crystal"},
            {"id": 2, "name": "Wireless Headphones", "price": 159.99, "image": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e", "description": "Noise-cancelling Bluetooth headphones"},
            {"id": 3, "name": "Smartphone", "price": 899.99, "image": "https://images.unsplash.com/photo-1598327105666-5b89351aff97", "description": "Latest flagship smartphone with 5G"},
            {"id": 4, "name": "Designer Sunglasses", "price": 129.99, "image": "https://images.unsplash.com/photo-1577803645773-f96470509666", "description": "UV protection polarized lenses"}
        ]
        with open(PRODUCTS_FILE, 'w') as f:
            json.dump(default_products, f)

init_files()

# Helper functions
def read_users():
    with open(USERS_FILE, 'r') as f:
        return json.load(f)

def write_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)

def read_products():
    with open(PRODUCTS_FILE, 'r') as f:
        return json.load(f)

def get_cart():
    return session.get('cart', [])

def update_cart(cart):
    session['cart'] = cart

# Routes
@app.route('/')
def home():
    session.clear()
    return render_template('signup.html')

@app.route('/signup', methods=['POST'])
def signup():
    name = request.form.get('name')
    password = request.form.get('password')
    telegram_id = request.form.get('telegram_id')
    
    if not all([name, password, telegram_id]):
        return render_template('signup.html', error="All fields are required")
    
    session['signup_data'] = {
        'name': name,
        'password': password,
        'telegram_id': telegram_id
    }
    
    return redirect(url_for('verify'))

@app.route('/verify')
def verify():
    if 'signup_data' not in session:
        return redirect(url_for('home'))
    return render_template('verify.html', telegram_id=session['signup_data']['telegram_id'])

@app.route('/send-otp')
def send_otp():
    if 'signup_data' not in session:
        return redirect(url_for('home'))
    
    telegram_id = session['signup_data']['telegram_id']
    try:
        response = requests.get(f'https://verification-api-bot.aimbox77.workers.dev/?telegramUserId={telegram_id}')
        otp_data = response.json()
        otp = otp_data.get('otp')
        
        if not otp:
            return render_template('verify.html', error="Failed to get OTP", telegram_id=telegram_id)
        
        # Save user with OTP
        user_data = {
            'name': session['signup_data']['name'],
            'password': session['signup_data']['password'],
            'telegram_id': telegram_id,
            'otp': otp,
            'login_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        users = read_users()
        users.append(user_data)
        write_users(users)
        
        session['verification_user'] = user_data
        return render_template('verify.html', otp_sent=True, telegram_id=telegram_id)
    
    except Exception as e:
        return render_template('verify.html', error=str(e), telegram_id=telegram_id)

@app.route('/verify-otp', methods=['POST'])
def verify_otp():
    if 'verification_user' not in session:
        return redirect(url_for('home'))
    
    user_otp = request.form.get('otp')
    stored_otp = session['verification_user']['otp']
    
    # Validate 6-digit OTP
    if len(user_otp) != 6:
        return render_template('verify.html', 
                              error="OTP must be 6 digits",
                              telegram_id=session['verification_user']['telegram_id'])
    
    if user_otp == stored_otp:
        session.pop('signup_data', None)
        session.pop('verification_user', None)
        session['logged_in'] = True
        session['user'] = {
            'name': session['verification_user']['name'],
            'telegram_id': session['verification_user']['telegram_id']
        }
        return redirect(url_for('shop'))
    
    return render_template('verify.html', error="Invalid OTP", telegram_id=session['verification_user']['telegram_id'])

@app.route('/shop')
def shop():
    if not session.get('logged_in'):
        return redirect(url_for('home'))
    
    products = read_products()
    return render_template('shop.html', products=products)

@app.route('/add-to-cart/<int:product_id>')
def add_to_cart(product_id):
    if not session.get('logged_in'):
        abort(403)
    
    products = read_products()
    product = next((p for p in products if p['id'] == product_id), None)
    
    if not product:
        abort(404)
    
    cart = get_cart()
    cart_item = next((item for item in cart if item['id'] == product_id), None)
    
    if cart_item:
        cart_item['quantity'] += 1
    else:
        product['quantity'] = 1
        cart.append(product)
    
    update_cart(cart)
    return jsonify(success=True)

@app.route('/remove-from-cart/<int:product_id>')
def remove_from_cart(product_id):
    if not session.get('logged_in'):
        abort(403)
    
    cart = get_cart()
    new_cart = [item for item in cart if item['id'] != product_id]
    update_cart(new_cart)
    return jsonify(success=True)

@app.route('/cart')
def cart():
    if not session.get('logged_in'):
        return redirect(url_for('home'))
    
    cart = get_cart()
    total = sum(item['price'] * item.get('quantity', 1) for item in cart)
    return render_template('cart.html', cart=cart, total=total)

@app.route('/checkout')
def checkout():
    if not session.get('logged_in'):
        return redirect(url_for('home'))
    
    session['cart'] = []
    return render_template('checkout.html')

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
        else:
            return render_template('admin_login.html', error="Invalid password")
    
    if not session.get('admin_logged_in'):
        return render_template('admin_login.html')
    
    users = read_users()
    last_10 = users[-10:][::-1]
    products = read_products()
    return render_template('admin.html', total_users=len(users), last_signups=last_10, products=products)

@app.route('/download-users')
def download_users():
    if not session.get('admin_logged_in'):
        abort(403)
    return send_file(USERS_FILE, as_attachment=True)

@app.route('/clear-users')
def clear_users():
    if not session.get('admin_logged_in'):
        abort(403)
    write_users([])
    return redirect(url_for('admin'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000, debug=True)
