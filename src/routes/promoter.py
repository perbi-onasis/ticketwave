from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from src.models.event import Event, TicketType, Promotion, EVENT_CATEGORIES
from src.models.ticket import Ticket
from src.models import db
from datetime import datetime
from functools import wraps
import secrets
from werkzeug.utils import secure_filename
import os

promoter = Blueprint('promoter', __name__)

# Configure upload folder
UPLOAD_FOLDER = 'src/static/uploads/events'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

VALID_CATEGORIES = ['concerts', 'sports', 'theatre', 'conferences', 'festivals']

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def promoter_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in or register as a promoter to create events.', 'info')
            return redirect(url_for('auth.login', next=url_for('promoter.create_event')))
            
        if not (current_user.is_promoter or current_user.is_admin):
            flash('Access denied. Only promoters and administrators can create events.', 'danger')
            return redirect(url_for('main.index'))
            
        return f(*args, **kwargs)
    return decorated_function

@promoter.route('/promoter/dashboard')
@login_required
@promoter_required
def dashboard():
    # Get promoter's events
    events = Event.query.filter_by(promoter=current_user.username).all()
    
    # Calculate sales statistics
    event_stats = {}
    total_sales = 0
    total_tickets = 0
    
    for event in events:
        # Get all completed ticket sales for this event
        completed_tickets = Ticket.query.filter_by(
            event_id=event.id,
            payment_status='completed'
        ).all()
        
        # Calculate event totals
        event_revenue = sum(ticket.price_paid for ticket in completed_tickets)
        tickets_sold = len(completed_tickets)
        
        # Calculate per ticket type statistics
        ticket_type_stats = {}
        for ticket_type in event.ticket_types:
            type_tickets = [t for t in completed_tickets if t.ticket_type_id == ticket_type.id]
            type_revenue = sum(t.price_paid for t in type_tickets)
            
            ticket_type_stats[ticket_type.id] = {
                'name': ticket_type.name,
                'sold': len(type_tickets),
                'revenue': type_revenue,
                'available': ticket_type.available,
                'total': ticket_type.quantity
            }
        
        # Store event statistics
        event_stats[event.id] = {
            'name': event.name,
            'date': event.date,
            'tickets_sold': tickets_sold,
            'revenue': event_revenue,
            'ticket_types': ticket_type_stats,
            'status': event.status
        }
        
        # Add to totals
        total_sales += event_revenue
        total_tickets += tickets_sold
    
    return render_template('promoter/dashboard.html',
                         events=events,
                         event_stats=event_stats,
                         total_sales=total_sales,
                         total_tickets=total_tickets)

@promoter.route('/promoter/events/create', methods=['GET', 'POST'])
@login_required
@promoter_required
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
                promoter=current_user.username,
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
                is_featured=False,  # Only admins can feature events
                status='approved'  # Changed from 'pending' to 'approved'
            )
            
            # Handle image upload
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(current_app.static_folder, 'uploads', filename)
                    file.save(file_path)
                    event.image_url = url_for('static', filename=f'uploads/{filename}')
            
            db.session.add(event)
            db.session.commit()
            
            # Updated success message and redirect to add ticket types
            flash('Event created successfully! Please add ticket types for your event.', 'success')
            return redirect(url_for('promoter.manage_tickets', event_id=event.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating event: {str(e)}', 'danger')
            print(f"Error creating event: {str(e)}")
            
    return render_template('shared/create_event.html',
                         categories=EVENT_CATEGORIES)

@promoter.route('/promoter/events/<int:event_id>/manage-tickets')
@login_required
def manage_tickets(event_id):
    if not current_user.is_promoter:
        flash('Access denied. Promoter privileges required.', 'danger')
        return redirect(url_for('main.index'))
        
    event = Event.query.get_or_404(event_id)
    if event.promoter != current_user.username:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('promoter.dashboard'))
    
    # Calculate statistics
    total_sold = 0
    total_revenue = 0
    if event.ticket_types:
        for ticket_type in event.ticket_types:
            sold = ticket_type.quantity - ticket_type.available
            total_sold += sold
            total_revenue += sold * ticket_type.price
    
    return render_template('promoter/manage_tickets.html',
                         event=event,
                         total_sold=total_sold,
                         total_revenue=total_revenue)

@promoter.route('/promoter/events/<int:event_id>/ticket-types/add', methods=['GET', 'POST'])
@login_required
@promoter_required
def add_ticket_type(event_id):
    event = Event.query.get_or_404(event_id)
    
    # Verify event belongs to promoter
    if event.promoter != current_user.username:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('promoter.dashboard'))
    
    if request.method == 'POST':
        try:
            # Get the selected ticket category name
            ticket_name = request.form['name']
            
            # Create default description based on ticket category if none provided
            description = request.form.get('description')
            if not description:
                descriptions = {
                    'VIP': 'Premium seating with exclusive benefits',
                    'Regular': 'Standard admission ticket',
                    'Early Bird': 'Discounted early purchase ticket',
                    'Student': 'Special rate for students with valid ID',
                    'Group': 'Special rate for group purchases',
                    'Premium': 'Enhanced experience with added benefits'
                }
                description = descriptions.get(ticket_name, '')

            ticket_type = TicketType(
                event_id=event.id,
                name=ticket_name,  # Use the category as the name
                description=description,
                price=float(request.form['price']),
                quantity=int(request.form['quantity']),
                available=int(request.form['quantity'])
            )
            
            db.session.add(ticket_type)
            db.session.commit()
            
            flash(f'{ticket_name} ticket type added successfully!', 'success')
            return redirect(url_for('promoter.manage_tickets', event_id=event.id))
            
        except Exception as e:
            db.session.rollback()
            flash('Error adding ticket type. Please try again.', 'danger')
            print(f"Error adding ticket type: {str(e)}")
            
    return render_template('promoter/add_ticket_type.html', event=event)

@promoter.route('/promoter/ticket-types/<int:ticket_type_id>/edit', methods=['GET', 'POST'])
@login_required
@promoter_required
def edit_ticket_type(ticket_type_id):
    ticket_type = TicketType.query.get_or_404(ticket_type_id)
    
    # Verify ticket type belongs to promoter's event
    if ticket_type.event.promoter != current_user.username:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('promoter.dashboard'))
    
    if request.method == 'POST':
        try:
            ticket_type.name = request.form['name']
            ticket_type.description = request.form.get('description')
            ticket_type.price = float(request.form['price'])
            
            # Handle quantity changes
            new_quantity = int(request.form.get('quantity', 0))
            if new_quantity > ticket_type.quantity:
                # Adding more tickets
                additional = new_quantity - ticket_type.quantity
                ticket_type.available += additional
                ticket_type.quantity = new_quantity
            
            db.session.commit()
            flash('Ticket type updated successfully!', 'success')
            
        except Exception as e:
            db.session.rollback()
            flash('Error updating ticket type. Please try again.', 'danger')
            print(f"Error updating ticket type: {str(e)}")
        
        return redirect(url_for('promoter.manage_tickets', event_id=ticket_type.event_id))
        
    return render_template('promoter/edit_ticket_type.html', 
                         ticket_type=ticket_type,
                         event=ticket_type.event)

@promoter.route('/promoter/ticket-types/<int:ticket_type_id>/delete', methods=['POST'])
@login_required
@promoter_required
def delete_ticket_type(ticket_type_id):
    ticket_type = TicketType.query.get_or_404(ticket_type_id)
    
    # Verify ticket type belongs to promoter's event
    if ticket_type.event.promoter != current_user.username:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('promoter.dashboard'))
    
    # Only allow deletion if no tickets have been sold
    if ticket_type.available < ticket_type.quantity:
        flash('Cannot delete ticket type with sold tickets', 'danger')
        return redirect(url_for('promoter.manage_tickets', event_id=ticket_type.event_id))
    
    try:
        db.session.delete(ticket_type)
        db.session.commit()
        flash('Ticket type deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting ticket type. Please try again.', 'danger')
        print(f"Error deleting ticket type: {str(e)}")
    
    return redirect(url_for('promoter.manage_tickets', event_id=ticket_type.event_id))

@promoter.route('/promoter/events/<int:event_id>/promotions')
@login_required
@promoter_required
def manage_promotions(event_id):
    event = Event.query.get_or_404(event_id)
    
    # Verify event belongs to promoter
    if event.promoter != current_user.username:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('promoter.dashboard'))
    
    active_promotions = Promotion.query.filter_by(
        event_id=event.id,
        is_active=True
    ).all()
    
    past_promotions = Promotion.query.filter_by(
        event_id=event.id,
        is_active=False
    ).all()
    
    return render_template('promoter/manage_promotions.html',
                         event=event,
                         active_promotions=active_promotions,
                         past_promotions=past_promotions)

@promoter.route('/promoter/events/<int:event_id>/promotions/add', methods=['GET', 'POST'])
@login_required
@promoter_required
def add_promotion(event_id):
    event = Event.query.get_or_404(event_id)
    
    # Verify event belongs to promoter
    if event.promoter != current_user.username:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('promoter.dashboard'))
    
    if request.method == 'POST':
        try:
            start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d')
            end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d')
            
            if end_date < start_date:
                flash('End date must be after start date', 'danger')
                return render_template('promoter/add_promotion.html', event=event)
            
            promotion = Promotion(
                event_id=event.id,
                code=request.form['code'].upper(),
                discount_amount=float(request.form['discount_percent']),
                discount_type='percentage',
                start_date=start_date,
                end_date=end_date,
                terms_conditions=request.form.get('terms_conditions'),
                is_active=True
            )
            
            db.session.add(promotion)
            db.session.commit()
            
            flash('Promotion added successfully!', 'success')
            return redirect(url_for('promoter.manage_promotions', event_id=event.id))
            
        except Exception as e:
            db.session.rollback()
            flash('Error adding promotion. Please try again.', 'danger')
            print(f"Error adding promotion: {str(e)}")
            
    return render_template('promoter/add_promotion.html', event=event)

@promoter.route('/promoter/promotions/<int:promotion_id>/deactivate', methods=['POST'])
@login_required
@promoter_required
def deactivate_promotion(promotion_id):
    promotion = Promotion.query.get_or_404(promotion_id)
    event = Event.query.get(promotion.event_id)
    
    # Verify event belongs to promoter
    if event.promoter != current_user.username:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('promoter.dashboard'))
    
    promotion.is_active = False
    db.session.commit()
    flash('Promotion has been deactivated', 'success')
    return redirect(url_for('promoter.manage_promotions', event_id=promotion.event_id))

@promoter.route('/promoter/events/<int:event_id>/sales')
@login_required
def event_sales(event_id):
    event = Event.query.get_or_404(event_id)
    if event.promoter != current_user.username:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('promoter.dashboard'))
    
    # Get all completed ticket sales
    tickets = Ticket.query.filter_by(
        event_id=event.id,
        payment_status='completed'
    ).order_by(Ticket.purchase_date.desc()).all()
    
    # Calculate statistics
    total_revenue = sum(ticket.price_paid for ticket in tickets)
    tickets_by_type = {}
    for ticket in tickets:
        ticket_type = ticket.ticket_type.name
        if ticket_type not in tickets_by_type:
            tickets_by_type[ticket_type] = {
                'count': 0,
                'revenue': 0,
                'promotions_used': 0
            }
        tickets_by_type[ticket_type]['count'] += 1
        tickets_by_type[ticket_type]['revenue'] += ticket.price_paid
        if ticket.used_promotion:
            tickets_by_type[ticket_type]['promotions_used'] += 1
    
    return render_template('promoter/event_sales.html',
                         event=event,
                         tickets=tickets,
                         total_revenue=total_revenue,
                         tickets_by_type=tickets_by_type)

@promoter.route('/promoter/events/<int:event_id>/sales-report')
@login_required
@promoter_required
def event_sales_report(event_id):
    event = Event.query.get_or_404(event_id)
    
    # Verify promoter owns this event
    if event.promoter != current_user.username:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('promoter.dashboard'))
    
    # Get all completed tickets for this event
    tickets = Ticket.query.filter_by(
        event_id=event_id,
        payment_status='completed'
    ).order_by(Ticket.purchase_date.desc()).all()
    
    # Calculate statistics
    total_sales = sum(ticket.price_paid for ticket in tickets)
    tickets_by_type = {}
    for ticket in tickets:
        if ticket.ticket_type.name not in tickets_by_type:
            tickets_by_type[ticket.ticket_type.name] = {
                'count': 0,
                'revenue': 0,
                'price': ticket.ticket_type.price
            }
        tickets_by_type[ticket.ticket_type.name]['count'] += 1
        tickets_by_type[ticket.ticket_type.name]['revenue'] += ticket.price_paid
    
    # Sales by date
    sales_by_date = {}
    for ticket in tickets:
        date = ticket.purchase_date.strftime('%Y-%m-%d')
        if date not in sales_by_date:
            sales_by_date[date] = {
                'count': 0,
                'revenue': 0
            }
        sales_by_date[date]['count'] += 1
        sales_by_date[date]['revenue'] += ticket.price_paid
    
    return render_template('promoter/sales_report.html',
                         event=event,
                         tickets=tickets,
                         total_sales=total_sales,
                         tickets_by_type=tickets_by_type,
                         sales_by_date=sales_by_date)

@promoter.route('/promoter/sales-reports')
@login_required
@promoter_required
def all_sales_reports():
    # Get all events by this promoter
    events = Event.query.filter_by(promoter=current_user.username).all()
    
    # Calculate statistics for each event
    event_stats = {}
    total_revenue = 0
    total_tickets = 0
    
    for event in events:
        tickets = Ticket.query.filter_by(
            event_id=event.id,
            payment_status='completed'
        ).all()
        
        event_revenue = sum(ticket.price_paid for ticket in tickets)
        total_revenue += event_revenue
        total_tickets += len(tickets)
        
        event_stats[event.id] = {
            'tickets_sold': len(tickets),
            'revenue': event_revenue,
            'ticket_types': {}
        }
        
        # Stats by ticket type
        for ticket in tickets:
            tt_name = ticket.ticket_type.name
            if tt_name not in event_stats[event.id]['ticket_types']:
                event_stats[event.id]['ticket_types'][tt_name] = {
                    'sold': 0,
                    'revenue': 0,
                    'total': ticket.ticket_type.quantity,
                    'available': ticket.ticket_type.available
                }
            event_stats[event.id]['ticket_types'][tt_name]['sold'] += 1
            event_stats[event.id]['ticket_types'][tt_name]['revenue'] += ticket.price_paid
    
    return render_template('promoter/all_sales_reports.html',
                         events=events,
                         event_stats=event_stats,
                         total_revenue=total_revenue,
                         total_tickets=total_tickets) 