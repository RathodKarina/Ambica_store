from flask import Flask, redirect, url_for, flash, session, request
from models import db, User, Product, Order, OrderItem, Category, Newsletter, Review
from flask_login import LoginManager, logout_user, current_user
from werkzeug.security import generate_password_hash
import uuid
import os

app = Flask(__name__)
app.config.from_object('config.Config')

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.before_request
def enforce_single_session():
    if request.endpoint and 'static' in request.endpoint:
        return
    
    if current_user.is_authenticated:
        if session.get('session_token') != current_user.session_token:
            logout_user()
            flash("You have been logged out because your account was accessed from another device.", "error")
            return redirect(url_for('auth.login'))

@app.context_processor
def inject_cart_count():
    cart_count = 0
    if current_user.is_authenticated:
        from models import Cart
        cart_items = Cart.query.filter_by(user_id=current_user.id).all()
        cart_count = sum(item.quantity for item in cart_items)
    return dict(cart_count=cart_count)

# Register Blueprints
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.main import main_bp

app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(main_bp)

def seed_database():
    import random
    from datetime import datetime, timedelta

    if User.query.filter_by(username='admin').first() is None:
        admin_user = User(
            username='admin',
            email='admin@ambicastore.com',
            phone='0000000000',
            password=generate_password_hash('admin123'),
            is_admin=True
        )
        db.session.add(admin_user)
        db.session.commit()
        
    if User.query.filter_by(username='student').first() is None:
        student_user = User(
            username='student',
            email='student@university.edu',
            phone='9876543210',
            password=generate_password_hash('student123'),
            is_admin=False
        )
        db.session.add(student_user)
        db.session.commit()

    if Category.query.count() == 0:
        categories = [
            Category(name="Classical Flutes", image_url="/static/images/Bansuri.png"),
            Category(name="Stringed Instruments", image_url="/static/images/Violin.png"),
            Category(name="Percussion", image_url="/static/images/Steel tabala.png"),
            Category(name="Modern Electronics", image_url="/static/images/Electric Wind with Headphones.png")
        ]
        db.session.bulk_save_objects(categories)
        db.session.commit()
        
    if Product.query.count() == 0:
        c_string = Category.query.filter_by(name="Stringed Instruments").first()
        c_perc = Category.query.filter_by(name="Percussion").first()
        c_flute = Category.query.filter_by(name="Classical Flutes").first()
        c_elec = Category.query.filter_by(name="Modern Electronics").first()
        
        products = [
            Product(name="Premium Bansuri", price=2500.00, description="Authentic hand-made bamboo flute for classical Indian music.", image_url="/static/images/Bansuri.png", category_id=c_flute.id if c_flute else None, is_new=True, is_trending=True),
            Product(name="Kids Musical Set", price=1200.00, description="Comfy cubs 4-pieces kids musical instrument set.", image_url="/static/images/Comfy cubs 4-pieces kids Musical Instrument.png", category_id=c_perc.id if c_perc else None, is_new=False, is_trending=True),
            Product(name="Electric Wind Instrument", price=15500.00, description="Digital electric wind instrument with headphones.", image_url="/static/images/Electric Wind with Headphones.png", category_id=c_elec.id if c_elec else None, is_new=True, is_trending=True),
            Product(name="Professional Steel Tabla", price=6500.00, description="High quality steel tabla set.", image_url="/static/images/Steel tabala.png", category_id=c_perc.id if c_perc else None, is_new=False, is_trending=True),
            Product(name="Traditional Instrument", price=4500.00, description="Classic traditional instrument for authentic sounds.", image_url="/static/images/Traditional instrument.png", category_id=c_string.id if c_string else None, is_new=False, is_trending=False),
            Product(name="Acoustic Violin", price=8999.00, description="Beautifully crafted acoustic violin.", image_url="/static/images/Violin.png", category_id=c_string.id if c_string else None, is_new=False, is_trending=True)
        ]
        db.session.bulk_save_objects(products)
        db.session.commit()
        
    if Review.query.count() == 0:
        reviews = [
            Review(name="Rahul K.", message="The classical bansuri I bought here is magnificent. The tuning is flawless and the wood quality is superb.", rating=5),
            Review(name="Sneha P.", message="Incredible customer support! They helped me choose the perfect beginner violin. Highly recommend Ambica Store!", rating=5),
            Review(name="Ankit S.", message="The steel tabla set exceeds my expectations. Perfect resonance. Ordered on Monday, got it by Wednesday.", rating=5)
        ]
        db.session.bulk_save_objects(reviews)
        db.session.commit()

from sqlalchemy import text

with app.app_context():
    # Force reset database schema on Render for the new models
    # db.drop_all() # REMOVED: This was causing all your registered users to be deleted on restart!
    db.create_all()
    
    # Auto-migration script to securely add columns without data loss
    try:
        db.session.execute(text("ALTER TABLE cart ADD COLUMN color VARCHAR(50) DEFAULT 'Standard'"))
        db.session.execute(text("ALTER TABLE cart ADD COLUMN tier VARCHAR(50) DEFAULT 'Standard'"))
        db.session.commit()
    except Exception:
        db.session.rollback()
        
    try:
        db.session.execute(text("ALTER TABLE order_item ADD COLUMN color VARCHAR(50) DEFAULT 'Standard'"))
        db.session.execute(text("ALTER TABLE order_item ADD COLUMN tier VARCHAR(50) DEFAULT 'Standard'"))
        db.session.commit()
    except Exception:
        db.session.rollback()
        
    try:
        db.session.execute(text("ALTER TABLE product ADD COLUMN price_low FLOAT"))
        db.session.execute(text("ALTER TABLE product ADD COLUMN price_premium FLOAT"))
        db.session.execute(text("ALTER TABLE product ADD COLUMN image_url_black TEXT"))
        db.session.execute(text("ALTER TABLE product ADD COLUMN image_url_brown TEXT"))
        db.session.execute(text("ALTER TABLE product ADD COLUMN image_url_cream TEXT"))
        db.session.commit()
    except Exception:
        db.session.rollback()
        
    seed_database()

if __name__ == '__main__':
    app.run(debug=True)