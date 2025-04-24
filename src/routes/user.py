from flask import Blueprint, render_template, redirect, url_for, flash, send_file, request, jsonify, current_app, session
from flask_login import login_required, current_user
from src.models.ticket import Ticket
from src.models.event import Event, TicketType, Promotion
from src.models import db
from datetime import datetime, timedelta
from src.utils.email import send_tickets_email
import qrcode
import io
import uuid
import requests
import secrets
import base64
from src.utils.payment import PaystackPayment

user = Blueprint('user', __name__)

@user.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_admin:
        return redirect(url_for('admin.dashboard'))
    elif current_user.is_promoter:
        return redirect(url_for('promoter.dashboard'))
    
    # Get user's tickets
    my_tickets = Ticket.query.filter_by(user_id=current_user.id).all()
    
    # Get upcoming events based on user preferences
    upcoming_events = Event.query.filter(
        Event.date >= datetime.now(),
        Event.status == 'approved'
    ).order_by(Event.date).limit(5).all()
    
    return render_template('user/dashboard.html',
                         tickets=my_tickets,
                         upcoming_events=upcoming_events,
                         now=datetime.now())

@user.route('/my-tickets')
@login_required
def my_tickets():
    if current_user.is_admin:
        return redirect(url_for('admin.dashboard'))
    
    tickets = Ticket.query.filter_by(
        user_id=current_user.id
    ).order_by(Ticket.purchase_date.desc()).all()
    
    return render_template('user/my_tickets.html', tickets=tickets)

@user.route('/ticket/<int:ticket_id>')
@login_required
def view_ticket(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    if ticket.user_id != current_user.id:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('user.dashboard'))
    return render_template('user/ticket_detail.html', ticket=ticket)

@user.route('/ticket/<int:ticket_id>/download')
@login_required
def download_ticket(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    if ticket.user_id != current_user.id:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('user.dashboard'))
    
    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(ticket.generate_qr_code())
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Save QR code to bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes)
    img_bytes.seek(0)
    
    return send_file(
        img_bytes,
        mimetype='image/png',
        as_attachment=True,
        download_name=f'ticket_{ticket.ticket_number}.png'
    )

@user.route('/events')
def events():
    # Get filter parameters
    category = request.args.get('category')
    search = request.args.get('q')
    date_filter = request.args.get('date')
    price_filter = request.args.get('price')
    sort_by = request.args.get('sort', 'date')  # Default sort by date
    
    # Base query for upcoming events
    query = Event.query.filter(
        Event.date >= datetime.now()
    )
    
    # Apply search filter
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            db.or_(
                Event.name.ilike(search_term),
                Event.description.ilike(search_term),
                Event.venue.ilike(search_term),
                Event.category.ilike(search_term)
            )
        )
    
    # Apply category filter
    if category:
        query = query.filter(Event.category == category)
    
    # Apply date filter
    if date_filter:
        today = datetime.now().date()
        if date_filter == 'today':
            query = query.filter(db.func.date(Event.date) == today)
        elif date_filter == 'tomorrow':
            query = query.filter(db.func.date(Event.date) == today + timedelta(days=1))
        elif date_filter == 'this_week':
            end_of_week = today + timedelta(days=7)
            query = query.filter(db.func.date(Event.date).between(today, end_of_week))
        elif date_filter == 'this_weekend':
            # Calculate next weekend
            days_until_weekend = (5 - today.weekday()) % 7
            weekend_start = today + timedelta(days=days_until_weekend)
            weekend_end = weekend_start + timedelta(days=2)
            query = query.filter(db.func.date(Event.date).between(weekend_start, weekend_end))
        elif date_filter == 'this_month':
            next_month = today.replace(day=28) + timedelta(days=4)
            end_of_month = next_month - timedelta(days=next_month.day)
            query = query.filter(db.func.date(Event.date).between(today, end_of_month))
    
    # Apply price filter
    if price_filter:
        if price_filter == 'free':
            query = query.join(TicketType).filter(TicketType.price == 0)
        elif price_filter == 'paid':
            query = query.join(TicketType).filter(TicketType.price > 0)
        elif price_filter == 'under_50':
            query = query.join(TicketType).filter(TicketType.price < 50)
        elif price_filter == 'under_100':
            query = query.join(TicketType).filter(TicketType.price < 100)
    
    # Apply sorting
    if sort_by == 'date':
        query = query.order_by(Event.date)
    elif sort_by == 'price_low':
        query = query.join(TicketType).order_by(TicketType.price)
    elif sort_by == 'price_high':
        query = query.join(TicketType).order_by(TicketType.price.desc())
    elif sort_by == 'popularity':
        # Sort by number of tickets sold
        query = query.outerjoin(Ticket).group_by(Event.id).order_by(db.func.count(Ticket.id).desc())
    
    # Execute query
    events = query.all()
    
    # Get all categories for filter options
    categories = [
        ('nightlife_parties', 'Nightlife & Parties'),
        ('movies_cinema', 'Movies & Cinema'),
        ('arts_theatre', 'Arts & Theatre'),
        ('food_drinks', 'Food & Drinks'),
        ('networking', 'Networking'),
        ('travel_outdoor', 'Travel & Outdoor'),
        ('professional', 'Professional'),
        ('health_wellness', 'Health & Wellness'),
        ('family_education', 'Family & Education'),
        ('charity_causes', 'Charity & Causes'),
        ('science_technology', 'Science & Technology'),
        ('religion_spirituality', 'Religion & Spirituality'),
        ('community_culture', 'Community & Culture'),
        ('fashion', 'Fashion'),
        ('esports', 'Esports'),
        ('sports', 'Sports'),
        ('other', 'Other')
    ]
    
    return render_template('user/events.html',
                         events=events,
                         categories=categories,
                         current_category=category,
                         search=search,
                         date_filter=date_filter,
                         price_filter=price_filter,
                         sort_by=sort_by)

@user.route('/event/<int:event_id>')
def event_detail(event_id):
    event = Event.query.get_or_404(event_id)
    if event.status != 'approved':
        flash('This event is not currently available.', 'warning')
        return redirect(url_for('user.events'))
    return render_template('user/event_detail.html', 
                         event=event,
                         now=datetime.now())

@user.route('/purchase/<int:event_id>', methods=['GET', 'POST'])
def purchase_tickets(event_id):
    event = Event.query.get_or_404(event_id)
    
    if request.method == 'POST':
        try:
            quantities = {}
            total_amount = 0
            verification_required = False
            
            # Process each ticket type quantity
            for key, value in request.form.items():
                if key.startswith('quantity_') and value != '0':
                    ticket_type_id = int(key.split('_')[1])
                    quantity = int(value)
                    ticket_type = TicketType.query.get_or_404(ticket_type_id)
                    
                    if ticket_type.available < quantity:
                        flash(f'Only {ticket_type.available} tickets available for {ticket_type.name}', 'danger')
                        return redirect(url_for('user.purchase_tickets', event_id=event_id))
                    
                    if ticket_type.requires_verification:
                        verification_required = True
                    
                    quantities[ticket_type_id] = quantity
                    total_amount += ticket_type.price * quantity
            
            if not quantities:
                flash('Please select at least one ticket.', 'warning')
                return redirect(url_for('user.purchase_tickets', event_id=event_id))
            
            # Store transaction details in session
            session['payment_details'] = {
                'event_id': event_id,
                'quantities': quantities,
                'total_amount': total_amount,
                'guest_name': request.form.get('guest_name'),
                'guest_email': request.form.get('guest_email'),
                'guest_phone': request.form.get('guest_phone'),
                'verification_required': verification_required
            }
            
            # Initialize Paystack payment
            paystack = PaystackPayment()
            reference = f"TKT-{secrets.token_hex(6)}"
            
            # Initialize payment
            payment = paystack.initialize_payment(
                email=request.form.get('guest_email'),
                amount=total_amount,
                reference=reference,
                callback_url=url_for('user.verify_payment', _external=True)
            )
            
            if payment and payment.get('authorization_url'):
                # Store reference in session
                session['payment_details']['reference'] = reference
                return redirect(payment['authorization_url'])
            
            flash('Error initializing payment. Please try again.', 'danger')
            return redirect(url_for('user.purchase_tickets', event_id=event_id))
            
        except Exception as e:
            print(f"Purchase error: {str(e)}")
            flash('Error processing purchase. Please try again.', 'danger')
            return redirect(url_for('user.purchase_tickets', event_id=event_id))
    
    return render_template('user/event_detail.html', event=event)

@user.route('/verify-payment')
def verify_payment():
    try:
        reference = request.args.get('reference')
        if not reference:
            flash('No payment reference provided', 'danger')
            return redirect(url_for('main.index'))
        
        # Get payment details from session
        payment_details = session.get('payment_details')
        if not payment_details or payment_details['reference'] != reference:
            flash('Invalid payment session', 'danger')
            return redirect(url_for('main.index'))
        
        # Verify payment with Paystack
        paystack = PaystackPayment()
        verification = paystack.verify_payment(reference)
        
        if verification and verification['status'] == 'success':
            try:
                # Create tickets
                tickets_created = []
                event = Event.query.get(payment_details['event_id'])
                
                for ticket_type_id, quantity in payment_details['quantities'].items():
                    ticket_type = TicketType.query.get(ticket_type_id)
                    
                    if ticket_type.available < quantity:
                        raise ValueError(f"Not enough tickets available for {ticket_type.name}")
                    
                    for _ in range(quantity):
                        ticket = Ticket(
                            event_id=event.id,
                            ticket_type_id=ticket_type_id,
                            price_paid=ticket_type.price,
                            payment_status='completed',
                            payment_method='paystack',
                            transaction_id=reference,
                            ticket_number=f"TKT-{secrets.token_hex(8).upper()}",
                            purchase_date=datetime.now(),
                            guest_name=payment_details['guest_name'],
                            guest_email=payment_details['guest_email'],
                            guest_phone=payment_details['guest_phone']
                        )
                        
                        # Generate QR code for the ticket
                        qr_data = f"Ticket #{ticket.ticket_number}\nEvent: {event.name}\nDate: {event.date.strftime('%B %d, %Y at %I:%M %p')}\nVenue: {event.venue}"
                        qr = qrcode.QRCode(version=1, box_size=10, border=5)
                        qr.add_data(qr_data)
                        qr.make(fit=True)
                        img = qr.make_image(fill_color="black", back_color="white")
                        
                        # Convert QR code to base64
                        img_bytes = io.BytesIO()
                        img.save(img_bytes, format='PNG')
                        img_bytes.seek(0)
                        ticket.qr_code = base64.b64encode(img_bytes.read()).decode('utf-8')
                        
                        ticket_type.available -= 1
                        db.session.add(ticket)
                        tickets_created.append(ticket)
                
                db.session.commit()
                
                # Send confirmation email
                send_tickets_email(payment_details['guest_email'], tickets_created, event)
                
                # Clear session
                session.pop('payment_details', None)
                
                flash('Payment successful! Your tickets have been generated.', 'success')
                return render_template('user/purchase_confirmation.html', tickets=tickets_created)
                
            except Exception as e:
                db.session.rollback()
                flash('Error processing tickets. Please contact support.', 'danger')
                print(f"Ticket generation error: {str(e)}")
                return redirect(url_for('main.index'))
        
        flash('Payment verification failed', 'danger')
        return redirect(url_for('main.index'))
        
    except Exception as e:
        flash('Error processing payment', 'danger')
        print(f"Payment verification error: {str(e)}")
        return redirect(url_for('main.index'))