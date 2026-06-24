from flask import (Blueprint, request, jsonify,
                   render_template, session, current_app)
from models import db, Order, OrderItem, Product
import stripe
import os

payments_bp = Blueprint('payments', __name__, url_prefix='/payments')

def enviar_correo_confirmacion(order):
    """
    Envía correo de confirmación usando Resend.
    Funciona en Render gratuito sin bloqueos SMTP.
    """
    import resend

    resend.api_key = os.getenv('RESEND_API_KEY')

    # Construir filas de productos
    items_html = ""
    for item in order.items:
        items_html += f"""
        <tr>
            <td style="padding:10px 8px;border-bottom:1px solid #e0f0e0;">
                {item.product.name}
            </td>
            <td style="padding:10px 8px;border-bottom:1px solid #e0f0e0;
                       text-align:center;">
                {item.quantity}
            </td>
            <td style="padding:10px 8px;border-bottom:1px solid #e0f0e0;
                       text-align:right;">
                $ {item.subtotal:,.0f} COP
            </td>
        </tr>
        """

    metodo = "💳 Tarjeta de crédito" if order.payment_method == 'stripe' else "🚚 Contra entrega"
    estado = "Pagado" if order.payment_method == 'stripe' else "Pendiente de pago"

    html = f"""
    <!DOCTYPE html>
    <html>
    <body style="margin:0;padding:20px;background:#f5f5f5;
                 font-family:'Segoe UI',sans-serif;">

    <div style="max-width:600px;margin:0 auto;background:#ffffff;
                border-radius:12px;overflow:hidden;
                border:1px solid #e0f0e0;">

        <!-- Header -->
        <div style="background:#39ff14;padding:28px;text-align:center;">
            <h1 style="margin:0;color:#1a1a1a;font-size:1.8rem;font-weight:900;">
                🎌 GepicToys
            </h1>
            <p style="margin:6px 0 0;color:#1a1a1a;font-size:1rem;">
                ¡Tu pedido fue confirmado!
            </p>
        </div>

        <!-- Cuerpo -->
        <div style="padding:28px;">
            <p style="font-size:1rem;color:#1a1a1a;margin-bottom:6px;">
                Hola <strong>{order.customer_name}</strong>,
            </p>
            <p style="color:#555;line-height:1.6;">
                Tu pedido <strong>#{order.id}</strong> fue registrado exitosamente.
                Llegará a tu dirección en
                <strong>máximo 5 días hábiles</strong>. 🚀
            </p>

            <!-- Detalle del pedido -->
            <h3 style="color:#1a7a00;border-bottom:2px solid #39ff14;
                        padding-bottom:8px;margin-top:24px;">
                📦 Detalle del pedido
            </h3>
            <table style="width:100%;border-collapse:collapse;margin-top:8px;">
                <thead>
                    <tr style="background:#f0fff0;">
                        <th style="padding:10px 8px;text-align:left;
                                   color:#1a7a00;font-size:0.9rem;">
                            Producto
                        </th>
                        <th style="padding:10px 8px;text-align:center;
                                   color:#1a7a00;font-size:0.9rem;">
                            Cant.
                        </th>
                        <th style="padding:10px 8px;text-align:right;
                                   color:#1a7a00;font-size:0.9rem;">
                            Subtotal
                        </th>
                    </tr>
                </thead>
                <tbody>
                    {items_html}
                </tbody>
            </table>

            <!-- Total -->
            <div style="background:#f0fff0;border-radius:8px;padding:14px;
                        margin-top:16px;text-align:right;">
                <span style="font-size:1.2rem;font-weight:900;color:#1a7a00;">
                    Total: $ {order.total:,.0f} COP
                </span>
            </div>

            <!-- Info entrega -->
            <div style="background:#fff8e1;border-left:4px solid #f39c12;
                        padding:14px 16px;margin-top:20px;
                        border-radius:0 8px 8px 0;">
                <p style="margin:0;color:#555;line-height:1.8;font-size:0.92rem;">
                    📍 <strong>Dirección:</strong>
                        {order.customer_address}<br>
                    📞 <strong>Teléfono:</strong>
                        {order.customer_phone or 'No proporcionado'}<br>
                    💳 <strong>Método de pago:</strong> {metodo}<br>
                    📋 <strong>Estado:</strong> {estado}<br>
                    📅 <strong>Entrega estimada:</strong> máximo 5 días hábiles
                </p>
            </div>

            <p style="color:#555;margin-top:20px;font-size:0.92rem;line-height:1.6;">
                Si tienes alguna pregunta sobre tu pedido contáctanos.
                ¡Gracias por comprar en GepicToys! 🎌
            </p>
        </div>

        <!-- Footer -->
        <div style="background:#f0fff0;padding:16px;text-align:center;
                    border-top:1px solid #e0f0e0;">
            <p style="margin:0;color:#888;font-size:0.82rem;">
                GepicToys · Los mejores muñecos anime de Colombia
            </p>
        </div>

    </div>
    </body>
    </html>
    """

    try:
        params = {
            "from":    "GepicToys <onboarding@resend.dev>",
            "to":      [order.customer_email],
            "subject": f"✅ Pedido #{order.id} confirmado - GepicToys",
            "html":    html,
        }
        email = resend.Emails.send(params)
        print(f"✅ Correo enviado - ID: {email['id']}")
    except Exception as e:
        print(f"❌ Error enviando correo: {e}")

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
    Guarda el pedido en BD, descuenta stock,
    limpia el carrito y envía correo de confirmación.
    """
    data   = request.get_json()
    cart   = session.get('cart', {})
    method = data.get('payment_method', 'stripe')

    if not cart:
        return jsonify({'error': 'Carrito vacío'}), 400

    # Estado según método de pago
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

    # Crear items y descontar stock
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

    # Limpiar carrito
    session.pop('cart', None)

    # Enviar correo — no bloquea el pedido si falla
    try:
        print(f"📧 Enviando correo a {order.customer_email}...")
        enviar_correo_confirmacion(order)
    except Exception as e:
        print(f"❌ Error de correo: {e}")

    return jsonify({'success': True, 'orderId': order.id})

@payments_bp.route('/webhook', methods=['POST'])
def webhook():
    """
    Stripe llama aquí cuando cambia el estado de un pago.
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