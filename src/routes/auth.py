from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from src.models.user import User
from src.models import db
from datetime import datetime
from src.utils.email import send_verification_email
from werkzeug.security import generate_password_hash, check_password_hash
from src.models.event import EVENT_CATEGORIES
from main import CATEGORY_ICONS

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        # Redirect to appropriate dashboard based on role
        if current_user.is_admin:
            return redirect(url_for('admin.dashboard'))
        elif current_user.is_promoter:
            return redirect(url_for('promoter.dashboard'))
        return redirect(url_for('user.dashboard'))

    next_page = request.args.get('next')
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password:
            flash('Please provide both email and password.', 'danger')
            return redirect(url_for('auth.login', next=next_page))
        
        user = User.query.filter_by(email=email).first()
        
        if not user:
            flash('Email not found.', 'danger')
            return redirect(url_for('auth.login', next=next_page))
        
        if not user.check_password(password):
            flash('Invalid password.', 'danger')
            return redirect(url_for('auth.login', next=next_page))
        
        login_user(user)
        
        # Handle next parameter and role-based redirects
        if next_page:
            if 'create_event' in next_page and (user.is_admin or user.is_promoter):
                return redirect(next_page)
            elif 'admin.dashboard' in next_page and user.is_admin:
                return redirect(next_page)
        
        # Default redirects based on role
        if user.is_admin:
            return redirect(url_for('admin.dashboard'))
        elif user.is_promoter:
            return redirect(url_for('promoter.dashboard'))
        return redirect(url_for('user.dashboard'))
    
    return render_template('auth/login.html',
                         next=next_page,
                         categories=EVENT_CATEGORIES,
                         category_icons=CATEGORY_ICONS)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not username or not email or not password:
            flash('All fields are required.', 'danger')
            return redirect(url_for('auth.register'))
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
            return redirect(url_for('auth.register'))
            
        if User.query.filter_by(email=email).first():
            flash('Email already exists.', 'danger')
            return redirect(url_for('auth.register'))
            
        new_user = User(
            username=username,
            email=email,
            password=generate_password_hash(password),
            role='promoter',
            is_promoter=True,
            is_verified=True  # Auto-verify for now
        )
        
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! You can now login as a promoter.', 'success')
            return redirect(url_for('auth.login', next=url_for('promoter.create_event')))
        except Exception as e:
            db.session.rollback()
            flash('Error creating account. Please try again.', 'danger')
            print(f"Registration error: {str(e)}")
            
    return render_template('auth/register.html',
                         categories=EVENT_CATEGORIES,
                         category_icons=CATEGORY_ICONS)

    
@auth.route('/verify/<token>')
def verify_email(token):
    user = User.query.filter_by(verification_token=token).first()
    if user:
        user.is_verified = True
        user.verification_token = None
        db.session.commit()
        flash('Your email has been verified! You can now log in.', 'success')
    else:
        flash('Invalid verification token.', 'danger')
    return redirect(url_for('auth.login'))

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))

@auth.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        # Get form data
        username = request.form.get('username')
        email = request.form.get('email')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        current_password = request.form.get('current_password')
        
        # Verify current password
        if not current_user.check_password(current_password):
            flash('Current password is incorrect.', 'danger')
            return redirect(url_for('auth.edit_profile'))
        
        # Check if username or email already exists
        if username != current_user.username and User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
            return redirect(url_for('auth.edit_profile'))
            
        if email != current_user.email and User.query.filter_by(email=email).first():
            flash('Email already exists.', 'danger')
            return redirect(url_for('auth.edit_profile'))
        
        # Update password if provided
        if new_password:
            if new_password != confirm_password:
                flash('New passwords do not match.', 'danger')
                return redirect(url_for('auth.edit_profile'))
            current_user.password = generate_password_hash(new_password)
        
        # Update user information
        current_user.username = username
        current_user.email = email
        
        try:
            db.session.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('auth.edit_profile'))
        except Exception as e:
            db.session.rollback()
            flash('Error updating profile. Please try again.', 'danger')
            print(f"Profile update error: {str(e)}")
            
    return render_template('auth/edit_profile.html') 

# src/routes/auth.py
from datetime import datetime, timedelta

@auth.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        
        if user:
            token = user.generate_reset_token()
            db.session.commit()
            send_password_reset_email(user.email, token)
            flash('Password reset instructions have been sent to your email.', 'info')
            return redirect(url_for('auth.login'))
            
        flash('Email not found.', 'danger')
        return redirect(url_for('auth.forgot_password'))
        
    return render_template('auth/forgot_password.html')

@auth.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
        
    user = User.query.filter_by(reset_token=token).first()
    
    if not user or user.reset_token_expiry < datetime.utcnow():
        flash('Invalid or expired password reset link.', 'danger')
        return redirect(url_for('auth.forgot_password'))
        
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('auth.reset_password', token=token))
            
        user.set_password(password)
        user.reset_token = None
        user.reset_token_expiry = None
        db.session.commit()
        
        flash('Your password has been reset. You can now login.', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('auth/reset_password.html')