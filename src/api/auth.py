import re

from flask import Blueprint, request, jsonify

from utilities.redis_data import redis_manager

auth = Blueprint('auth', __name__)


def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


@auth.route('/api/subscribe', methods=['POST'])
def api_subscribe():
    """API endpoint for newsletter subscription.

    Authentication (login/signup/logout) is owned by the Spring gateway +
    Supabase. Flask only handles the newsletter subscription list.
    """
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400

    subscribe_email = data.get('email', '').strip().lower()

    if not subscribe_email:
        return jsonify({'success': False, 'error': 'Please enter a valid email address'}), 400

    if not validate_email(subscribe_email):
        return jsonify({'success': False, 'error': 'Please enter a valid email address'}), 400

    try:
        existing = redis_manager.get_subscription_by_email(subscribe_email)
        if existing:
            return jsonify({
                'success': False,
                'error': 'This email is already subscribed.'
            }), 409

        redis_manager.save_subscription(subscribe_email)
        return jsonify({
            'success': True,
            'message': 'Thank you for subscribing to our newsletter!'
        })
    except Exception:
        return jsonify({'success': False, 'error': 'Subscription failed. Please try again.'}), 500
