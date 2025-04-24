from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from src.models.event import Event, TicketType, Promotion, EVENT_CATEGORIES
from src.models.ticket import Ticket
from src.models import db
from datetime import datetime, timedelta
from src.utils.email import send_promotion_email
from src.models.user import User
from functools import wraps
from werkzeug.utils import secure_filename
import os

admin = Blueprint('admin', __name__)

# Add these imports at the top
import os
from werkzeug.utils import secure_filename

# Add this function after the imports
def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Add admin_required decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('Access denied. Admin privileges required.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

@admin.route('/admin')
@login_required
@admin_required
def dashboard():
    events = Event.query.all()
    tickets = TicketType.query.all()
    promotions = Promotion.query.all()
    
    return render_template('admin/dashboard.html', 
                         events=events,
                         tickets=tickets,
                         promotions=promotions)

@admin.route('/admin/events/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_event():
    if request.method == 'POST':
        try:
            # Get form data
            name = request.form.get('name')
            description = request.form.get('description')
            date = datetime.strptime(request.form.get('date'), '%Y-%m-%dT%H:%M')
            end_date = None
            if request.form.get('end_date'):
                end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%dT%H:%M')
            
            # Create new event
            event = Event(
                name=name,
                description=description,
                category=request.form.get('category'),
                promoter=current_user.username,  # Admin is creating the event
                date=date,
                end_date=end_date,
                venue=request.form.get('venue'),
                address=request.form.get('address'),
                city=request.form.get('city'),
                max_capacity=request.form.get('max_capacity'),
                age_restriction=request.form.get('age_restriction'),
                website_url=request.form.get('website_url'),
                contact_email=request.form.get('contact_email'),
                contact_phone=request.form.get('contact_phone'),
                is_featured=bool(request.form.get('is_featured')),
                status='approved'  # Auto-approve admin-created events
            )
            
            # Handle image upload
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    # Use the correct path joining
                    file_path = os.path.join(current_app.static_folder, 'uploads', filename)
                    file.save(file_path)
                    event.image_url = url_for('static', filename=f'uploads/{filename}')
            
            db.session.add(event)
            db.session.commit()
            
            flash('Event created successfully!', 'success')
            return redirect(url_for('admin.dashboard'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating event: {str(e)}', 'danger')
            print(f"Error creating event: {str(e)}")
            
    return render_template('shared/create_event.html',
                         categories=EVENT_CATEGORIES)

@admin.route('/admin/events/<int:event_id>/tickets/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_ticket_type(event_id):
    event = Event.query.get_or_404(event_id)
    
    if request.method == 'POST':
        ticket_type = TicketType(
            event_id=event.id,
            name=request.form['name'],
            price=float(request.form['price']),
            quantity=int(request.form['quantity']),
            available=int(request.form['quantity']),
            description=request.form['description']
        )
        db.session.add(ticket_type)
        db.session.commit()
        flash('Ticket type added successfully!', 'success')
        return redirect(url_for('admin.dashboard'))
        
    return render_template('admin/add_ticket_type.html', event=event)

@admin.route('/admin/events/<int:event_id>/promotions')
@login_required
@admin_required
def manage_promotions(event_id):
    event = Event.query.get_or_404(event_id)
    current_time = datetime.now()
    
    # Get active promotions
    active_promotions = Promotion.query.filter(
        Promotion.event_id == event_id,
        Promotion.is_active == True,
        Promotion.end_date >= current_time
    ).all()
    
    # Get expired promotions
    expired_promotions = Promotion.query.filter(
        Promotion.event_id == event_id,
        Promotion.is_active == True,
        Promotion.end_date < current_time
    ).all()
    
    return render_template('admin/manage_promotions.html',
                         event=event,
                         active_promotions=active_promotions,
                         expired_promotions=expired_promotions)

@admin.route('/admin/events/<int:event_id>/promotions/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_promotion(event_id):
    event = Event.query.get_or_404(event_id)
    
    if request.method == 'POST':
        try:
            start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d')
            end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d')
            
            if end_date < start_date:
                flash('End date must be after start date', 'danger')
                return render_template('admin/add_promotion.html', event=event)
            
            # Get the promoter's email from the event
            promoter = User.query.filter_by(username=event.promoter).first()
            if not promoter:
                flash('Event promoter not found', 'danger')
                return render_template('admin/add_promotion.html', event=event)
            
            promotion = Promotion(
                event_id=event.id,
                code=request.form['code'].upper(),
                discount_percent=float(request.form['discount_percent']),
                start_date=start_date,
                end_date=end_date,
                terms_conditions=request.form.get('terms_conditions'),
                is_active=True
            )
            
            db.session.add(promotion)
            db.session.commit()
            
            # Send email to promoter
            send_promotion_email(promoter.email, promotion, event)
            
            flash('Promotion added successfully!', 'success')
            return redirect(url_for('admin.manage_promotions', event_id=event.id))
            
        except ValueError as e:
            flash('Invalid date format. Please use YYYY-MM-DD format.', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding promotion: {str(e)}', 'danger')
            print(f"Error adding promotion: {str(e)}")
            
    return render_template('admin/add_promotion.html', event=event)

@admin.route('/promotions/<int:promotion_id>/deactivate', methods=['POST'])
@login_required
@admin_required
def deactivate_promotion(promotion_id):
    promotion = Promotion.query.get_or_404(promotion_id)
    promotion.is_active = False
    db.session.commit()
    flash('Promotion has been deactivated.', 'success')
    return redirect(url_for('admin.dashboard'))

@admin.route('/admin/reports')
@login_required
@admin_required
def sales_reports():
    try:
        # Get date range from query parameters
        from_date = request.args.get('from_date', None)
        to_date = request.args.get('to_date', None)
        
        # Base query for completed tickets
        query = Ticket.query.filter_by(payment_status='completed')
        
        # Apply date filters if provided
        if from_date:
            query = query.filter(Ticket.purchase_date >= datetime.strptime(from_date, '%Y-%m-%d'))
        if to_date:
            query = query.filter(Ticket.purchase_date <= datetime.strptime(to_date, '%Y-%m-%d') + timedelta(days=1))
        
        # Get all tickets
        tickets = query.all()
        
        # Calculate total sales
        total_sales = sum(ticket.price_paid for ticket in tickets)
        total_tickets = len(tickets)
        
        # Group by event
        events = Event.query.all()
        event_sales = {}
        
        for event in events:
            event_tickets = [t for t in tickets if t.event_id == event.id]
            if event_tickets:
                event_sales[event.name] = {
                    'count': len(event_tickets),
                    'total': sum(t.price_paid for t in event_tickets),
                    'promotions_used': len([t for t in event_tickets if t.promotion_id]),
                    'avg_price': sum(t.price_paid for t in event_tickets) / len(event_tickets),
                    'date': event.date.strftime('%Y-%m-%d'),
                    'status': event.status
                }
        
        # Calculate additional statistics
        stats = {
            'total_revenue': total_sales,
            'total_tickets': total_tickets,
            'avg_ticket_price': total_sales / total_tickets if total_tickets > 0 else 0,
            'total_events': len(event_sales),
            'promotions_used': len([t for t in tickets if t.promotion_id]),
            'sales_by_month': {},
            'sales_by_payment_method': {}
        }
        
        # Sales by month
        for ticket in tickets:
            month = ticket.purchase_date.strftime('%Y-%m')
            if month not in stats['sales_by_month']:
                stats['sales_by_month'][month] = {
                    'count': 0,
                    'revenue': 0
                }
            stats['sales_by_month'][month]['count'] += 1
            stats['sales_by_month'][month]['revenue'] += ticket.price_paid
        
        # Sales by payment method
        for ticket in tickets:
            method = ticket.payment_method
            if method not in stats['sales_by_payment_method']:
                stats['sales_by_payment_method'][method] = {
                    'count': 0,
                    'revenue': 0
                }
            stats['sales_by_payment_method'][method]['count'] += 1
            stats['sales_by_payment_method'][method]['revenue'] += ticket.price_paid
        
        return render_template('admin/sales_reports.html',
                             total_sales=total_sales,
                             event_sales=event_sales,
                             stats=stats,
                             from_date=from_date,
                             to_date=to_date)
                             
    except Exception as e:
        flash('Error generating sales report. Please try again.', 'danger')
        print(f"Sales report error: {str(e)}")
        return redirect(url_for('admin.dashboard'))

@admin.route('/admin/events')
@login_required
@admin_required
def view_events():
    events = Event.query.all()
    return render_template('admin/view_events.html', events=events)

@admin.route('/admin/events/approve/<int:event_id>', methods=['POST'])
@login_required
@admin_required
def approve_event(event_id):
    event = Event.query.get_or_404(event_id)
    event.status = 'approved'
    db.session.commit()
    flash('Event has been approved!', 'success')
    return redirect(url_for('admin.dashboard'))

@admin.route('/admin/events/reject/<int:event_id>', methods=['POST'])
@login_required
@admin_required
def reject_event(event_id):
    event = Event.query.get_or_404(event_id)
    event.status = 'rejected'
    db.session.commit()
    flash('Event has been rejected.', 'warning')
    return redirect(url_for('admin.dashboard'))

@admin.route('/admin/events/<int:event_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_event(event_id):
    event = Event.query.get_or_404(event_id)
    try:
        db.session.delete(event)
        db.session.commit()
        flash('Event deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting event.', 'danger')
    return redirect(url_for('admin.view_events')) 