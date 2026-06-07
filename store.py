from flask import (Blueprint, render_template, redirect,
                   url_for, request, flash, session, current_app)
from models import Product

store_bp = Blueprint('store', __name__, url_prefix='/store')

def get_cart():
    return session.get('cart', {})

def save_cart(cart):
    session['cart'] = cart
    session.modified = True

def cart_total(cart):
    return sum(item['price'] * item['quantity'] for item in cart.values())

@store_bp.route('/')
def index():
    products = (Product.query
                .filter_by(active=True)
                .filter(Product.stock > 0)
                .all())
    cart = get_cart()
    cart_count = sum(item['quantity'] for item in cart.values())
    return render_template('store/index.html',
                           products=products,
                           cart_count=cart_count)

@store_bp.route('/cart/add/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    quantity = int(request.form.get('quantity', 1))
    cart = get_cart()
    pid = str(product_id)

    if pid in cart:
        nueva = cart[pid]['quantity'] + quantity
        cart[pid]['quantity'] = min(nueva, product.stock)
    else:
        cart[pid] = {
            'name': product.name,
            'price': product.price,
            'quantity': quantity,
            'image': product.image_url,
        }

    save_cart(cart)
    flash(f'"{product.name}" agregado al carrito 🛒', 'success')
    return redirect(url_for('store.index'))

@store_bp.route('/cart')
def view_cart():
    cart = get_cart()
    total = cart_total(cart)
    return render_template('store/cart.html',
                           cart=cart,
                           total=total)

@store_bp.route('/cart/update/<product_id>', methods=['POST'])
def update_cart(product_id):
    cart = get_cart()
    quantity = int(request.form.get('quantity', 1))

    if product_id in cart:
        if quantity <= 0:
            del cart[product_id]
            flash('Producto eliminado del carrito', 'info')
        else:
            product = Product.query.get(int(product_id))
            cart[product_id]['quantity'] = min(quantity, product.stock)

    save_cart(cart)
    return redirect(url_for('store.view_cart'))

@store_bp.route('/cart/remove/<product_id>')
def remove_from_cart(product_id):
    cart = get_cart()
    if product_id in cart:
        nombre = cart[product_id]['name']
        del cart[product_id]
        save_cart(cart)
        flash(f'"{nombre}" eliminado del carrito', 'info')
    return redirect(url_for('store.view_cart'))

@store_bp.route('/checkout')
def checkout():
    cart = get_cart()
    if not cart:
        flash('Tu carrito está vacío', 'error')
        return redirect(url_for('store.index'))

    total = cart_total(cart)
    stripe_public_key = current_app.config['STRIPE_PUBLIC_KEY']
    return render_template('store/checkout.html',
                           cart=cart,
                           total=total,
                           stripe_public_key=stripe_public_key)