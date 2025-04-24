# from flask import Flask, render_template, request, redirect, url_for, flash, session # type: ignore
# from datetime import datetime, timedelta
# from functools import wraps
# import os

# app = Flask(__name__)
# app.secret_key = os.urandom(24)

# # Database setup (using SQLAlchemy)
# from flask_sqlalchemy import SQLAlchemy

# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ticketing.db'
# app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# db = SQLAlchemy(app)

# Database Models
# class User(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     username = db.Column(db.String(80), unique=True, nullable=False)
#     password = db.Column(db.String(120), nullable=False)
#     is_admin = db.Column(db.Boolean, default=False)

# class Event(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(100), nullable=False)
#     promoter = db.Column(db.String(100), nullable=False)
#     date = db.Column(db.DateTime, nullable=False)
#     venue = db.Column(db.String(100), nullable=False)
#     ticket_types = db.relationship('TicketType', backref='event', lazy=True)
#     promotions = db.relationship('Promotion', backref='event', lazy=True)

# class TicketType(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
#     name = db.Column(db.String(50), nullable=False)
#     price = db.Column(db.Float, nullable=False)
#     total_quantity = db.Column(db.Integer, nullable=False)
#     available_quantity = db.Column(db.Integer, nullable=False)
#     description = db.Column(db.Text)

# class Promotion(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
#     code = db.Column(db.String(20), nullable=False)
#     discount = db.Column(db.Float, nullable=False)
#     start_date = db.Column(db.DateTime, nullable=False)
#     end_date = db.Column(db.DateTime, nullable=False)
#     terms_conditions = db.Column(db.Text)

# Login decorator
# def login_required(f):
#     @wraps(f)
#     def decorated_function(*args, **kwargs):
#         if 'user_id' not in session:
#             return redirect(url_for('login'))
#         return f(*args, **kwargs)
#     return decorated_function

# def admin_required(f):
#     @wraps(f)
#     def decorated_function(*args, **kwargs):
#         if 'user_id' not in session:
#             return redirect(url_for('login'))
#         user = User.query.get(session['user_id'])
#         if not user or not user.is_admin:
#             flash('Admin access required')
#             return redirect(url_for('index'))
#         return f(*args, **kwargs)
#     return decorated_function

# Routes
# @app.route('/')
# def index():
#     events = Event.query.all()
#     return render_template('index.html', events=events)

# @app.route('/login', methods=['GET', 'POST'])
# def login():
#     if request.method == 'POST':
#         username = request.form['username']
#         password = request.form['password']
#         user = User.query.filter_by(username=username, password=password).first()
#         
#         if user:
#             session['user_id'] = user.id
#             flash('Logged in successfully')
#             return redirect(url_for('admin_dashboard' if user.is_admin else 'customer_dashboard'))
#         flash('Invalid credentials')
#     return render_template('login.html')

# @app.route('/register', methods=['GET', 'POST'])
# def register():
#     if request.method == 'POST':
#         username = request.form['username']
#         password = request.form['password']
#         
#         if User.query.filter_by(username=username).first():
#             flash('Username already exists')
#             return redirect(url_for('register'))
#             
#         user = User(username=username, password=password)
#         db.session.add(user)
#         db.session.commit()
#         flash('Registration successful')
#         return redirect(url_for('login'))
#     return render_template('register.html')

# @app.route('/admin')
# @admin_required
# def admin_dashboard():
#     events = Event.query.all()
#     return render_template('admin/dashboard.html', events=events)

# @app.route('/admin/events/create', methods=['GET', 'POST'])
# @admin_required
# def create_event():
#     if request.method == 'POST':
#         event = Event(
#             name=request.form['name'],
#             promoter=request.form['promoter'],
#             date=datetime.strptime(request.form['date'], '%Y-%m-%d'),
#             venue=request.form['venue']
#         )
#         db.session.add(event)
#         db.session.commit()
#         flash('Event created successfully')
#         return redirect(url_for('admin_dashboard'))
#     return render_template('admin/create_event.html')

# Add more routes for other functionalities...

# if __name__ == '__main__':
#     with app.app_context():
#         db.create_all()
#     app.run(debug=True) 