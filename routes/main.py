from flask import Blueprint, render_template, request, redirect, flash, current_app
from flask_login import login_required, current_user
from models import db, Product, Cart, Order, OrderItem, Category, Newsletter, Review

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def home():
    # Fetch data dynamically for the new homepage architecture
    categories = Category.query.all()
    # Fetch trending or latest 8 products
    trending_products = Product.query.filter_by(is_trending=True).limit(8).all()
    if not trending_products:
        trending_products = Product.query.order_by(Product.id.desc()).limit(8).all()
        
    reviews = Review.query.limit(3).all()
    
    return render_template('index.html', categories=categories, trending_products=trending_products, reviews=reviews)

@main_bp.route('/products')
def products():
    products = Product.query.all()
    return render_template('products.html', products=products)

@main_bp.route('/product/<int:id>')
def product_detail(id):
    product = Product.query.get(id)
    return render_template('product_detail.html', product=product)

@main_bp.route('/add_to_cart/<int:id>', methods=['GET', 'POST'])
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

@main_bp.route('/cart')
@login_required
def cart():
    items = Cart.query.filter_by(user_id=current_user.id).all()
    last_order = Order.query.filter_by(user_id=current_user.id).order_by(Order.date_ordered.desc()).first()
    default_address = last_order.delivery_address if last_order else ""
    return render_template('cart.html', items=items, default_address=default_address)

@main_bp.route('/update_cart/<int:id>', methods=['POST'])
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

@main_bp.route('/remove_from_cart/<int:id>')
@login_required
def remove_from_cart(id):
    item = Cart.query.get(id)
    if item and item.user_id == current_user.id:
        db.session.delete(item)
        db.session.commit()
    return redirect('/cart')

@main_bp.route('/checkout', methods=['POST'])
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
    db.session.flush()
    
    for item in cart_items:
        order_item = OrderItem(
            order_id=new_order.id,
            product_id=item.product_id,
            quantity=item.quantity,
            price_at_purchase=item.product.price
        )
        db.session.add(order_item)
        db.session.delete(item)
    
    db.session.commit()
    flash("Checkout successful! Your order has been placed.", "success")
    return redirect(f'/order_success/{new_order.id}')

@main_bp.route('/order_success/<int:id>')
@login_required
def order_success(id):
    order = Order.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    return render_template('order_success.html', order=order)

@main_bp.route('/profile')
@login_required
def profile():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.date_ordered.desc()).all()
    return render_template('profile.html', orders=orders)

@main_bp.route('/user_cancel_order/<int:order_id>', methods=['POST'])
@login_required
def user_cancel_order(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        flash("Unauthorized action.", "error")
        return redirect('/profile')
    
    if order.status != 'Cancelled':
        order.status = 'Cancelled'
        order.cancellation_reason = request.form.get('reason', 'No reason provided by user')
        db.session.commit()
        flash("Your order has been cancelled.", "success")
        
    return redirect('/profile')

@main_bp.route('/subscribe', methods=['POST'])
def subscribe():
    email = request.form.get('email')
    if email:
        exists = Newsletter.query.filter_by(email=email).first()
        if not exists:
            new_sub = Newsletter(email=email)
            db.session.add(new_sub)
            db.session.commit()
            flash("Thank you for subscribing to our newsletter!", "success")
        else:
            flash("You are already subscribed!", "success")
    return redirect('/')
