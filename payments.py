# ── payments.py ────────────────────────────────────────────────
# Maneja la integración con Stripe para procesar pagos.
# Flujo: crear PaymentIntent → confirmar pago → guardar pedido → webhook

from flask import (Blueprint, request, jsonify,
                   render_template, session, current_app)
from models import db, Order, OrderItem, Product
import stripe

payments_bp = Blueprint('payments', __name__, url_prefix='/payments')

@payments_bp.route('/create-payment-intent', methods=['POST'])
def create_payment_intent():
    """
    El frontend llama aquí para iniciar el proceso de pago.
    Stripe necesita un PaymentIntent antes de mostrar el formulario de tarjeta.
    Devuelve un clientSecret que Stripe.js usa para procesar la tarjeta.
    """
    stripe.api_key = current_app.config['STRIPE_SECRET_KEY']
    data = request.get_json()
    cart = session.get('cart', {})

    if not cart:
        return jsonify({'error': 'Carrito vacío'}), 400

    # Stripe trabaja en centavos (la unidad mínima de la moneda)
    total_cents = int(sum(
        item['price'] * item['quantity'] for item in cart.values()
    ) * 100)

    # Crear el PaymentIntent en Stripe
    intent = stripe.PaymentIntent.create(
        amount   = total_cents,
        currency = 'cop',   # pesos colombianos
        metadata = {'customer_email': data.get('email', '')}
    )

    return jsonify({
        'clientSecret':    intent.client_secret,  # necesario para Stripe.js
        'paymentIntentId': intent.id              # lo guardamos con el pedido
    })

@payments_bp.route('/confirm-order', methods=['POST'])
def confirm_order():
    """
    El frontend llama aquí DESPUÉS de que Stripe confirmó el pago exitosamente.
    Guarda el pedido en la base de datos y descuenta el stock.
    """
    data = request.get_json()
    cart = session.get('cart', {})

    if not cart:
        return jsonify({'error': 'Carrito vacío'}), 400

    # Crear el pedido principal con los datos del cliente
    order = Order(
        customer_name          = data['name'],
        customer_email         = data['email'],
        customer_phone         = data.get('phone', ''),
        customer_address       = data.get('address', ''),
        stripe_payment_intent  = data['paymentIntentId'],
        status = 'pagado',
        total  = sum(item['price'] * item['quantity'] for item in cart.values())
    )
    db.session.add(order)
    db.session.flush()  # genera el order.id sin hacer commit aún

    # Crear un OrderItem por cada producto del carrito
    for pid, item in cart.items():
        product = Product.query.get(int(pid))
        if product:
            db.session.add(OrderItem(
                order_id   = order.id,
                product_id = product.id,
                seller_id  = product.created_by,  # vendedor dueño del producto
                quantity   = item['quantity'],
                unit_price = item['price'],
                subtotal   = item['price'] * item['quantity']
            ))
            # Descontar del stock inmediatamente
            product.stock -= item['quantity']

    db.session.commit()
    session.pop('cart', None)  # limpiar el carrito después de la compra

    return jsonify({'success': True, 'orderId': order.id})

@payments_bp.route('/webhook', methods=['POST'])
def webhook():
    """
    Stripe llama automáticamente aquí cuando el estado de un pago cambia.
    Útil para manejar pagos fallidos, reembolsos, disputas, etc.
    La firma se verifica con el webhook secret para evitar fraudes.
    """
    stripe.api_key = current_app.config['STRIPE_SECRET_KEY']
    payload    = request.data
    sig_header = request.headers.get('Stripe-Signature')

    try:
        # Verificar que el webhook viene realmente de Stripe
        event = stripe.Webhook.construct_event(
            payload, sig_header,
            current_app.config['STRIPE_WEBHOOK_SECRET']
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        return '', 400  # firma inválida

    # Manejar pago fallido
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
    """Página de confirmación que se muestra después de un pago exitoso."""
    order = Order.query.get_or_404(order_id)
    return render_template('store/order_success.html', order=order)