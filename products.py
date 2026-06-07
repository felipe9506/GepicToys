from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_required, current_user
from models import db, Product
import os
import time
from werkzeug.utils import secure_filename

products_bp = Blueprint('products', __name__, url_prefix='/products')

EXTENSIONES_PERMITIDAS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    """Verifica que el archivo sea una imagen válida"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in EXTENSIONES_PERMITIDAS

def guardar_imagen(archivo):
    """Guarda la imagen en static/images/ y devuelve la URL"""
    if archivo and allowed_file(archivo.filename):
        filename = secure_filename(archivo.filename)
        nombre, extension = os.path.splitext(filename)
        filename = f"{nombre}_{int(time.time())}{extension}"

        # Crear la carpeta si no existe
        carpeta = os.path.join(current_app.root_path, 'static', 'images')
        os.makedirs(carpeta, exist_ok=True)

        ruta = os.path.join(carpeta, filename)
        archivo.save(ruta)
        return url_for('static', filename=f'images/{filename}')
    return None

@products_bp.route('/')
@login_required
def list_products():
    products = Product.query.all()
    return render_template('products.html', products=products)

@products_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_product():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        price = float(request.form.get('price'))
        stock = int(request.form.get('stock'))

        # Subir imagen desde el PC
        imagen_url = None
        archivo = request.files.get('imagen')
        if archivo and archivo.filename != '':
            imagen_url = guardar_imagen(archivo)

        product = Product(
            name=name,
            description=description,
            price=price,
            stock=stock,
            image_url=imagen_url,
            created_by=current_user.id
        )
        db.session.add(product)
        db.session.commit()
        flash(f'Producto "{name}" agregado exitosamente ✅', 'success')
        return redirect(url_for('products.list_products'))

    return render_template('add_product.html', product=None)

@products_bp.route('/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)

    if request.method == 'POST':
        product.name = request.form.get('name')
        product.price = float(request.form.get('price'))
        product.stock = int(request.form.get('stock'))
        product.description = request.form.get('description')
        product.active = 'active' in request.form

        # Verificar si subió imagen nueva
        archivo = request.files.get('imagen')
        if archivo and archivo.filename != '':
            nueva_url = guardar_imagen(archivo)
            if nueva_url:
                # Borrar imagen anterior si era local
                if product.image_url and 'static/images/' in product.image_url:
                    ruta_vieja = os.path.join(
                        current_app.root_path,
                        'static', 'images',
                        os.path.basename(product.image_url)
                    )
                    if os.path.exists(ruta_vieja):
                        os.remove(ruta_vieja)
                product.image_url = nueva_url

        db.session.commit()
        flash('Producto actualizado ✅', 'success')
        return redirect(url_for('products.list_products'))

    return render_template('add_product.html', product=product)

@products_bp.route('/delete/<int:product_id>')
@login_required
def delete_product(product_id):
    if current_user.role != 'gerente':
        flash('Solo el gerente puede eliminar productos', 'error')
        return redirect(url_for('products.list_products'))

    product = Product.query.get_or_404(product_id)

    # Borrar imagen local si existe
    if product.image_url and 'static/images/' in product.image_url:
        ruta = os.path.join(
            current_app.root_path,
            'static', 'images',
            os.path.basename(product.image_url)
        )
        if os.path.exists(ruta):
            os.remove(ruta)

    db.session.delete(product)
    db.session.commit()
    flash('Producto eliminado', 'success')
    return redirect(url_for('products.list_products'))