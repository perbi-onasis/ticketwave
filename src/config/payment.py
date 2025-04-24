import os

PAYSTACK_CONFIG = {
    'SECRET_KEY': os.getenv('PAYSTACK_SECRET_KEY'),
    'PUBLIC_KEY': os.getenv('PAYSTACK_PUBLIC_KEY'),
    'CURRENCY': 'GHS',  # Change according to your currency
    'PAYMENT_URL': 'https://api.paystack.co'
} 