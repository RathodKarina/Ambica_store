from flask import Blueprint, render_template, request, redirect, flash, current_app
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from sqlalchemy.exc import IntegrityError
from models import db, User, Product, Order, OrderItem, Cart
import os
import base64

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin')
@login_required
def admin_home():
    if not current_user.is_admin:
        return "Access denied: Admins only", 403
    return render_template('admin.html')

@admin_bp.route('/admin/products')
@login_required
def admin_products():
    if not current_user.is_admin:
        return "Access denied: Admins only", 403
    products = Product.query.all()
    return render_template('admin_products.html', products=products)

@admin_bp.route('/admin/customers')
@login_required
def admin_customers():
    if not current_user.is_admin:
        return "Access denied: Admins only", 403
    users = User.query.all()
    return render_template('admin_customers.html', users=users)

@admin_bp.route('/admin/orders')
@login_required
def admin_orders():
    if not current_user.is_admin:
        return "Access denied: Admins only", 403
    orders = Order.query.order_by(Order.date_ordered.desc()).all()
    return render_template('admin_orders.html', orders=orders)

@admin_bp.route('/admin/settings', methods=['GET', 'POST'])
@login_required
def admin_settings():
    if not current_user.is_admin or current_user.username != 'admin':
        flash("Access denied: Only the head Admin can change Store Settings.", "error")
        return redirect('/admin')
        
    if request.method == 'POST':
        image_file = request.files.get('qr_image')
        if image_file and image_file.filename != '':
            os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
            save_path = os.path.join(current_app.root_path, 'static', 'images', 'payment_qr.png')
            image_file.save(save_path)
            flash("Payment QR Code updated successfully!", "success")
            return redirect('/admin/settings')
            
    qr_exists = os.path.exists(os.path.join(current_app.root_path, 'static', 'images', 'payment_qr.png'))
    return render_template('admin_settings.html', qr_exists=qr_exists)

@admin_bp.route('/admin/settings/delete', methods=['POST'])
@login_required
def admin_delete_qr():
    if not current_user.is_admin or current_user.username != 'admin':
        flash("Access denied: Only the head Admin can delete QR code.", "error")
        return redirect('/admin')
        
    qr_path = os.path.join(current_app.root_path, 'static', 'images', 'payment_qr.png')
    if os.path.exists(qr_path):
        os.remove(qr_path)
        flash("Old Payment QR Code has been securely deleted!", "success")
    else:
        flash("No QR Code exists to delete.", "error")
        
    return redirect('/admin/settings')

@admin_bp.route('/admin/employees')
@login_required
def admin_employees():
    if not current_user.is_admin or current_user.username != 'admin':
        flash("Access denied: Only the head Admin can view Staff.", "error")
        return redirect('/admin')
    employees = User.query.filter_by(is_admin=True).all()
    return render_template('admin_employees.html', employees=employees)

@admin_bp.route('/admin/add_employee', methods=['GET', 'POST'])
@login_required
def admin_add_employee():
    if not current_user.is_admin or current_user.username != 'admin':
        flash("Access denied: Only the head Admin can add Staff.", "error")
        return redirect('/admin')
        
    if request.method == 'POST':
        secret_key = request.form.get('secret_key')
        if secret_key != current_app.config['EMPLOYEE_SECRET_KEY']:
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

@admin_bp.route('/admin/add', methods=['GET', 'POST'])
@login_required
def admin_add_product():
    if not current_user.is_admin:
        return "Access denied", 403
    if request.method == 'POST':
        def process_image(file_key):
            img_file = request.files.get(file_key)
            if img_file and img_file.filename != '':
                encoded = base64.b64encode(img_file.read()).decode('utf-8')
                return f"data:{img_file.mimetype};base64,{encoded}"
            return None
            
        product = Product(
            name=request.form['name'],
            price=float(request.form['price']),
            price_low=float(request.form.get('price_low')) if request.form.get('price_low') else None,
            price_premium=float(request.form.get('price_premium')) if request.form.get('price_premium') else None,
            description=request.form.get('description', ''),
            image_url=process_image('image') or '',
            image_url_black=process_image('image_black'),
            image_url_brown=process_image('image_brown'),
            image_url_cream=process_image('image_cream')
        )
        db.session.add(product)
        db.session.commit()
        return redirect('/admin/products')
    return render_template('admin_product_form.html')

@admin_bp.route('/admin/delete/<int:id>')
@login_required
def admin_delete_product(id):
    if not current_user.is_admin:
        return "Access denied", 403
    product = Product.query.get(id)
    if product:
        Cart.query.filter_by(product_id=id).delete()
        db.session.delete(product)
        db.session.commit()
    return redirect('/admin/products')

@admin_bp.route('/admin/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def admin_edit_product(id):
    if not current_user.is_admin:
        return "Access denied", 403
    
    product = Product.query.get_or_404(id)
    
    if request.method == 'POST':
        product.name = request.form['name']
        product.price = float(request.form['price'])
        if request.form.get('price_low'):
            product.price_low = float(request.form['price_low'])
        if request.form.get('price_premium'):
            product.price_premium = float(request.form['price_premium'])
            
        product.description = request.form.get('description', '')
        
        def process_image(file_key):
            img_file = request.files.get(file_key)
            if img_file and img_file.filename != '':
                encoded = base64.b64encode(img_file.read()).decode('utf-8')
                return f"data:{img_file.mimetype};base64,{encoded}"
            return None
            
        img_default = process_image('image')
        if img_default: product.image_url = img_default
        
        img_black = process_image('image_black')
        if img_black: product.image_url_black = img_black
        
        img_brown = process_image('image_brown')
        if img_brown: product.image_url_brown = img_brown
        
        img_cream = process_image('image_cream')
        if img_cream: product.image_url_cream = img_cream

        db.session.commit()
        flash("Product updated successfully!", "success")
        return redirect('/admin/products')
        
    return render_template('admin_edit_product_form.html', product=product)

@admin_bp.route('/admin/delete_order/<int:id>', methods=['POST'])
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

@admin_bp.route('/admin/accept_order/<int:id>', methods=['POST'])
@login_required
def admin_accept_order(id):
    if not current_user.is_admin:
        return "Access denied", 403
    order = Order.query.get(id)
    if order:
        # Re-using cancellation_reason column for the admin "Review" message to avoid DB migrations
        review_msg = request.form.get('reason', 'Order accepted.')
        order.status = 'Accepted'
        order.cancellation_reason = review_msg
        db.session.commit()
        flash("Order accepted and review sent to user.", "success")
    return redirect('/admin/orders')
