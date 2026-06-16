from flask import (Blueprint, request, jsonify,
                   render_template, session, current_app)
from models import db, Order, OrderItem, Product
import stripe

payments_bp = Blueprint('payments', __name__, url_prefix='/payments')

@payments_bp.route('/create-payment-intent', methods=['POST'])
def create_payment_intent():
    """
    Crea un PaymentIntent en Stripe.
    El frontend necesita el clientSecret para mostrar el formulario de tarjeta.
    """
    stripe.api_key = current_app.config['STRIPE_SECRET_KEY']
    data = request.get_json()
    cart = session.get('cart', {})

    if not cart:
        return jsonify({'error': 'Carrito vacío'}), 400

    # Stripe trabaja en centavos
    total_cents = int(sum(
        item['price'] * item['quantity'] for item in cart.values()
    ) * 100)

    intent = stripe.PaymentIntent.create(
        amount   = total_cents,
        currency = 'cop',
        metadata = {'customer_email': data.get('email', '')}
    )

    return jsonify({
        'clientSecret':    intent.client_secret,
        'paymentIntentId': intent.id
    })

@payments_bp.route('/confirm-order', methods=['POST'])
def confirm_order():
    """
    Guarda el pedido en la base de datos después de confirmar el pago.
    Soporta tanto Stripe como contra entrega.
    """
    data   = request.get_json()
    cart   = session.get('cart', {})
    method = data.get('payment_method', 'stripe')

    if not cart:
        return jsonify({'error': 'Carrito vacío'}), 400

    # Estado según método de pago
    # Stripe → pagado (ya se cobró)
    # Contra entrega → pendiente (se cobra al recibir)
    estado = 'pagado' if method == 'stripe' else 'pendiente'

    order = Order(
        customer_name         = data['name'],
        customer_email        = data['email'],
        customer_phone        = data.get('phone', ''),
        customer_address      = data.get('address', ''),
        stripe_payment_intent = data.get('paymentIntentId'),
        payment_method        = method,
        status                = estado,
        total                 = sum(
            item['price'] * item['quantity'] for item in cart.values()
        )
    )
    db.session.add(order)
    db.session.flush()

    # Crear un item por cada producto y descontar stock
    for pid, item in cart.items():
        product = Product.query.get(int(pid))
        if product:
            db.session.add(OrderItem(
                order_id   = order.id,
                product_id = product.id,
                seller_id  = product.created_by,
                quantity   = item['quantity'],
                unit_price = item['price'],
                subtotal   = item['price'] * item['quantity']
            ))
            product.stock -= item['quantity']

    db.session.commit()
    session.pop('cart', None)

    return jsonify({'success': True, 'orderId': order.id})

@payments_bp.route('/webhook', methods=['POST'])
def webhook():
    """
    Stripe llama aquí cuando el estado de un pago cambia.
    Verifica la firma para evitar fraudes.
    """
    stripe.api_key = current_app.config['STRIPE_SECRET_KEY']
    payload    = request.data
    sig_header = request.headers.get('Stripe-Signature')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header,
            current_app.config['STRIPE_WEBHOOK_SECRET']
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        return '', 400

    if event['type'] == 'payment_intent.payment_failed':
        intent = event['data']['object']
        order  = Order.query.filter_by(
            stripe_payment_intent=intent['id']
        ).first()
        if order:
            order.status = 'cancelado'
            db.session.commit()

    return '', 200

@payments_bp.route('/success/<int:order_id>')
def success(order_id):
    """Página de confirmación después del pago."""
    order = Order.query.get_or_404(order_id)
    return render_template('store/order_success.html', order=order)