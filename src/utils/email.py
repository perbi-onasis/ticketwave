from flask_mail import Message, Mail
from flask import current_app, url_for, render_template
from threading import Thread

mail = Mail()

def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)

def send_verification_email(email, token):
    verify_url = url_for('auth.verify_email', token=token, _external=True)
    msg = Message('Verify Your Email',
                  sender=current_app.config['MAIL_DEFAULT_SENDER'],
                  recipients=[email])
    msg.body = f'''To verify your email address visit the following link:
{verify_url}

If you did not make this request then simply ignore this email.
'''
    Thread(target=send_async_email,
           args=(current_app._get_current_object(), msg)).start()

def send_ticket_email(email, ticket):
    msg = Message('Your Event Ticket',
                  sender=current_app.config['MAIL_DEFAULT_SENDER'],
                  recipients=[email])
    
    msg.body = f'''Thank you for your purchase!

Event: {ticket.event.name}
Date: {ticket.event.date.strftime('%B %d, %Y')}
Venue: {ticket.event.venue}
Ticket Type: {ticket.ticket_type}
Price: ${ticket.price:.2f}

Please show this email at the event entrance.
Ticket ID: {ticket.id}

Enjoy the event!
'''
    Thread(target=send_async_email,
           args=(current_app._get_current_object(), msg)).start()

def send_promotion_email(promoter_email, promotion, event):
    msg = Message('New Promotion Added to Your Event',
                  sender=current_app.config['MAIL_DEFAULT_SENDER'],
                  recipients=[promoter_email])
    
    msg.body = f'''A new promotion has been added to your event: {event.name}

Promotion Details:
Code: {promotion.code}
Discount: {promotion.discount_percent}%
Valid from: {promotion.start_date.strftime('%B %d, %Y')}
Valid until: {promotion.end_date.strftime('%B %d, %Y')}

{promotion.terms_conditions if promotion.terms_conditions else ''}

This promotion is now active and can be used by customers.
'''
    Thread(target=send_async_email,
           args=(current_app._get_current_object(), msg)).start()

def send_tickets_email(email, tickets, event):
    msg = Message('Your Event Tickets',
                  sender=current_app.config['MAIL_DEFAULT_SENDER'],
                  recipients=[email])
    
    # Create email content
    msg.body = f'''Thank you for your purchase!

Event: {event.name}
Date: {event.date.strftime('%B %d, %Y at %I:%M %p')}
Venue: {event.venue}

Your Tickets:
'''
    
    # Add each ticket to the email
    for ticket in tickets:
        msg.body += f'''
----------------------------------------
Ticket Number: {ticket.ticket_number}
Type: {ticket.ticket_type.name}
Price Paid: ₵{ticket.price_paid:.2f}
'''
        if ticket.used_promotion:
            msg.body += f'Promotion Applied: {ticket.used_promotion.code}\n'
    
    msg.body += '''
----------------------------------------

Please show this email or your ticket numbers at the event entrance.
Enjoy the event!
'''
    
    Thread(target=send_async_email,
           args=(current_app._get_current_object(), msg)).start() 


# src/utils/email.py
def send_password_reset_email(email, token):
    reset_url = url_for('auth.reset_password', token=token, _external=True)
    msg = Message('Reset Your Password',
                  sender=current_app.config['MAIL_DEFAULT_SENDER'],
                  recipients=[email])
    msg.body = f'''To reset your password visit the following link:
{reset_url}

This link will expire in 1 hour.

If you did not make this request then simply ignore this email.
'''
    Thread(target=send_async_email,
           args=(current_app._get_current_object(), msg)).start()