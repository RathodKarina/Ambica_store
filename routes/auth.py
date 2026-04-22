from flask import Blueprint, render_template, request, redirect, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import IntegrityError
from models import db, User
import uuid

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect('/products')
        
    if request.method == 'POST':
        is_admin = (request.form['username'] == 'admin')
        hashed_password = generate_password_hash(request.form['password'])
        phone = request.form.get('phone', '')
        user = User(
            username=request.form['username'],
            email=request.form.get('email', None),
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
            flash("Account already exists! You simply need to login.", "success")
            return redirect('/login')
        except Exception as e:
            db.session.rollback()
            flash(f"An error occurred: {str(e)}", "error")
            return redirect('/register')
    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect('/products')
        
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form['email']).first()

        if user and check_password_hash(user.password, request.form['password']):
            login_user(user, remember=True)
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

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/login')
