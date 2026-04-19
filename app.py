from flask import Flask, render_template, request, redirect, url_for, flash, session
from models import db, User, Product, Cart, Order, OrderItem
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy.exc import IntegrityError
from datetime import timedelta
import os
import uuid

app = Flask(__name__)

# Load configuration from config.py
app.config.from_object('config.Config')

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.before_request
def enforce_single_session():
    # Allow static file requests without checking
    if request.endpoint and 'static' in request.endpoint:
        return
    
    if current_user.is_authenticated:
        if session.get('session_token') != current_user.session_token:
            logout_user()
            flash("You have been logged out because your account was accessed from another device.", "error")
            return redirect(url_for('login'))

# ---------------- HOME ----------------
@app.route('/')
def home():
    # Fetch the 4 most recently added products to showcase on the home page
    recent_products = Product.query.order_by(Product.id.desc()).limit(4).all()
    return render_template('index.html', recent_products=recent_products)

# ---------------- REGISTER ----------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Assign admin role if username is exactly 'admin'
        is_admin = (request.form['username'] == 'admin')
        hashed_password = generate_password_hash(request.form['password'])
        phone = request.form.get('phone', '')
        user = User(
            username=request.form['username'],
            phone=phone,
            password=hashed_password,
            is_admin=is_admin
        )
        try:
            db.session.add(user)
            db.session.commit()
            flash("Account created! You can now log in.", "success")
            return redirect('/login')
        except IntegrityError:
            db.session.rollback()
            flash("Username already exists. Please try another.", "error")
            return redirect('/register')
        except Exception as e:
            db.session.rollback()
            flash(f"An error occurred: {str(e)}", "error")
            return redirect('/register')
    return render_template('register.html')

# ---------------- LOGIN ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()

        if user and check_password_hash(user.password, request.form['password']):
            login_user(user, remember=True)
            # Create a new session token to invalidate other sessions
            new_token = str(uuid.uuid4())
            user.session_token = new_token
            db.session.commit()
            session['session_token'] = new_token
            
            flash("Logged in successfully!", "success")
            return redirect('/products')
        else:
            flash("Invalid credentials", "error")
            return redirect('/login')

    return render_template('login.html')

# ---------------- PRODUCTS ----------------
@app.route('/products')
def products():
    products = Product.query.all()
    return render_template('products.html', products=products)

# ---------------- PRODUCT DETAIL ----------------
@app.route('/product/<int:id>')
def product_detail(id):
    product = Product.query.get(id)
    return render_template('product_detail.html', product=product)

# ---------------- ADD TO CART ----------------
@app.route('/add_to_cart/<int:id>', methods=['GET', 'POST'])
@login_required
def add_to_cart(id):
    quantity = int(request.form.get('quantity', 1)) if request.method == 'POST' else 1
    cart_item = Cart.query.filter_by(product_id=id, user_id=current_user.id).first()
    if cart_item:
        cart_item.quantity += quantity
    else:
        cart_item = Cart(product_id=id, user_id=current_user.id, quantity=quantity)
        db.session.add(cart_item)
    db.session.commit()
    flash("Added to your cart!", "success")
    return redirect('/cart')

# ---------------- CART ----------------
@app.route('/cart')
@login_required
def cart():
    items = Cart.query.filter_by(user_id=current_user.id).all()
    last_order = Order.query.filter_by(user_id=current_user.id).order_by(Order.date_ordered.desc()).first()
    default_address = last_order.delivery_address if last_order else ""
    return render_template('cart.html', items=items, default_address=default_address)

# ---------------- UPDATE CART ----------------
@app.route('/update_cart/<int:id>', methods=['POST'])
@login_required
def update_cart(id):
    item = Cart.query.get(id)
    if item and item.user_id == current_user.id:
        new_quantity = int(request.form.get('quantity', 1))
        if new_quantity > 0:
            item.quantity = new_quantity
            db.session.commit()
        else:
            db.session.delete(item)
            db.session.commit()
    return redirect('/cart')

# ---------------- REMOVE FROM CART ----------------
@app.route('/remove_from_cart/<int:id>')
@login_required
def remove_from_cart(id):
    item = Cart.query.get(id)
    if item and item.user_id == current_user.id:
        db.session.delete(item)
        db.session.commit()
    return redirect('/cart')

# ---------------- CHECKOUT ----------------
@app.route('/checkout', methods=['POST'])
@login_required
def checkout():
    cart_items = Cart.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        return redirect('/cart')
    
    total_price = sum(item.product.price * item.quantity for item in cart_items)
    
    payment_method = request.form.get('payment_method', 'cash')
    delivery_address = request.form.get('delivery_address', '')
    new_order = Order(user_id=current_user.id, total_price=total_price, payment_method=payment_method, delivery_address=delivery_address)
    db.session.add(new_order)
    db.session.flush() # get new_order.id
    
    for item in cart_items:
        order_item = OrderItem(
            order_id=new_order.id,
            product_id=item.product_id,
            quantity=item.quantity,
            price_at_purchase=item.product.price
        )
        db.session.add(order_item)
        db.session.delete(item) # clear cart
    
    db.session.commit()
    flash("Checkout successful! Your order has been placed.", "success")
    return redirect(f'/order_success/{new_order.id}')

# ---------------- ORDER SUCCESS ----------------
@app.route('/order_success/<int:id>')
@login_required
def order_success(id):
    order = Order.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    return render_template('order_success.html', order=order)

# ---------------- PROFILE / ORDERS ----------------
@app.route('/profile')
@login_required
def profile():
    # User's order history
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.date_ordered.desc()).all()
    return render_template('profile.html', orders=orders)

# ---------------- LOGOUT ----------------
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/login')

# ---------------- ADMIN ----------------
@app.route('/admin')
@login_required
def admin():
    if not current_user.is_admin:
        return "Access denied: Admins only", 403
    return render_template('admin.html')

@app.route('/admin/products')
@login_required
def admin_products():
    if not current_user.is_admin:
        return "Access denied: Admins only", 403
    products = Product.query.all()
    return render_template('admin_products.html', products=products)

@app.route('/admin/customers')
@login_required
def admin_customers():
    if not current_user.is_admin:
        return "Access denied: Admins only", 403
    users = User.query.all()
    return render_template('admin_customers.html', users=users)

@app.route('/admin/orders')
@login_required
def admin_orders():
    if not current_user.is_admin:
        return "Access denied: Admins only", 403
    orders = Order.query.order_by(Order.date_ordered.desc()).all()
    return render_template('admin_orders.html', orders=orders)

@app.route('/admin/settings', methods=['GET', 'POST'])
@login_required
def admin_settings():
    # Only the original 'admin' user can change settings
    if not current_user.is_admin or current_user.username != 'admin':
        flash("Access denied: Only the head Admin can change Store Settings.", "error")
        return redirect('/admin')
        
    if request.method == 'POST':
        image_file = request.files.get('qr_image')
        if image_file and image_file.filename != '':
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            save_path = os.path.join(app.root_path, 'static', 'images', 'payment_qr.png')
            image_file.save(save_path)
            flash("Payment QR Code updated successfully!", "success")
            return redirect('/admin/settings')
            
    qr_exists = os.path.exists(os.path.join(app.root_path, 'static', 'images', 'payment_qr.png'))
    return render_template('admin_settings.html', qr_exists=qr_exists)

@app.route('/admin/settings/delete', methods=['POST'])
@login_required
def admin_delete_qr():
    if not current_user.is_admin or current_user.username != 'admin':
        flash("Access denied: Only the head Admin can delete QR code.", "error")
        return redirect('/admin')
        
    qr_path = os.path.join(app.root_path, 'static', 'images', 'payment_qr.png')
    if os.path.exists(qr_path):
        os.remove(qr_path)
        flash("Old Payment QR Code has been securely deleted!", "success")
    else:
        flash("No QR Code exists to delete.", "error")
        
    return redirect('/admin/settings')

@app.route('/admin/employees')
@login_required
def admin_employees():
    # Only the original 'admin' user can see the employee list
    if not current_user.is_admin or current_user.username != 'admin':
        flash("Access denied: Only the head Admin can view Staff.", "error")
        return redirect('/admin')
    employees = User.query.filter_by(is_admin=True).all()
    return render_template('admin_employees.html', employees=employees)

@app.route('/admin/add_employee', methods=['GET', 'POST'])
@login_required
def admin_add_employee():
    # Only the original 'admin' user can add new employees
    if not current_user.is_admin or current_user.username != 'admin':
        flash("Access denied: Only the head Admin can add Staff.", "error")
        return redirect('/admin')
        
    if request.method == 'POST':
        secret_key = request.form.get('secret_key')
        if secret_key != app.config['EMPLOYEE_SECRET_KEY']:
            flash("Invalid Employee Secret Key. Cannot add employee.", "error")
            return redirect('/admin/add_employee')
            
        hashed_password = generate_password_hash(request.form['password'])
        phone = request.form.get('phone', '')
        user = User(
            username=request.form['username'],
            phone=phone,
            password=hashed_password,
            is_admin=True
        )
        try:
            db.session.add(user)
            db.session.commit()
            flash("Employee account created successfully!", "success")
            return redirect('/admin')
        except IntegrityError:
            db.session.rollback()
            flash("Username already exists. Please try another.", "error")
            return redirect('/admin/add_employee')
            
    return render_template('admin_add_employee.html')

@app.route('/admin/add', methods=['GET', 'POST'])
@login_required
def admin_add_product():
    if not current_user.is_admin:
        return "Access denied", 403
    if request.method == 'POST':
        image_file = request.files.get('image')
        image_path = ''
        if image_file and image_file.filename != '':
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            filename = secure_filename(image_file.filename)
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image_file.save(save_path)
            # Use relative URL for frontend templates
            image_path = '/static/uploads/' + filename
            
        product = Product(
            name=request.form['name'],
            price=float(request.form['price']),
            description=request.form.get('description', ''),
            image_url=image_path
        )
        db.session.add(product)
        db.session.commit()
        return redirect('/admin/products')
    return render_template('admin_product_form.html')

@app.route('/admin/delete/<int:id>')
@login_required
def admin_delete_product(id):
    if not current_user.is_admin:
        return "Access denied", 403
    product = Product.query.get(id)
    if product:
        # Prevent integrity errors if it's in a cart
        Cart.query.filter_by(product_id=id).delete()
        db.session.delete(product)
        db.session.commit()
    return redirect('/admin/products')

@app.route('/admin/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def admin_edit_product(id):
    if not current_user.is_admin:
        return "Access denied", 403
    
    product = Product.query.get_or_404(id)
    
    if request.method == 'POST':
        product.name = request.form['name']
        product.price = float(request.form['price'])
        product.description = request.form.get('description', '')
        
        image_file = request.files.get('image')
        if image_file and image_file.filename != '':
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            filename = secure_filename(image_file.filename)
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image_file.save(save_path)
            product.image_url = '/static/uploads/' + filename
            
        db.session.commit()
        flash("Product updated successfully!", "success")
        return redirect('/admin/products')
        
    return render_template('admin_edit_product_form.html', product=product)


@app.route('/admin/delete_order/<int:id>', methods=['POST'])
@login_required
def admin_delete_order(id):
    if not current_user.is_admin:
        return "Access denied", 403
    order = Order.query.get(id)
    if order:
        reason = request.form.get('reason', 'No reason provided.')
        order.status = 'Cancelled'
        order.cancellation_reason = reason
        db.session.commit()
        flash("Order cancelled successfully.", "success")
    return redirect('/admin/orders')

def seed_database():
    if User.query.filter_by(username='admin').first() is None:
        admin_user = User(
            username='admin',
            phone='0000000000',
            password=generate_password_hash('admin123'),
            is_admin=True
        )
        db.session.add(admin_user)
        db.session.commit()
        
    if Product.query.count() == 0:
        products = [
            Product(name="Premium Bansuri", price=2500.00, description="Authentic hand-made bamboo flute for classical Indian music.", image_url="/static/images/Bansuri.png"),
            Product(name="Kids Musical Set", price=1200.00, description="Comfy cubs 4-pieces kids musical instrument set.", image_url="/static/images/Comfy cubs 4-pieces kids Musical Instrument.png"),
            Product(name="Electric Wind Instrument", price=15500.00, description="Digital electric wind instrument with headphones.", image_url="/static/images/Electric Wind with Headphones.png"),
            Product(name="Professional Steel Tabla", price=6500.00, description="High quality steel tabla set.", image_url="/static/images/Steel tabala.png"),
            Product(name="Traditional Instrument", price=4500.00, description="Classic traditional instrument for authentic sounds.", image_url="/static/images/Traditional instrument.png"),
            Product(name="Acoustic Violin", price=8999.00, description="Beautifully crafted acoustic violin.", image_url="/static/images/Violin.png")
        ]
        db.session.bulk_save_objects(products)
        db.session.commit()

# ---------------- INITIALIZATION ----------------
with app.app_context():
    db.create_all()
    seed_database()

# ---------------- RUN ----------------
if __name__ == '__main__':
    app.run(debug=True)