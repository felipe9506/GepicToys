from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_required, current_user
from models import db, Product
import os
import time
from werkzeug.utils import secure_filename

products_bp = Blueprint('products', __name__, url_prefix='/products')

EXTENSIONES_PERMITIDAS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

CATEGORIAS = [
    ('juguetes',    '🧸 Juguetes y Figuras'),
    ('billeteras',  '👜 Billeteras'),
    ('camisas',     '👕 Camisas'),
    ('bufandas',    '🧣 Bufandas'),
    ('accesorios',  '✨ Accesorios'),
]

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in EXTENSIONES_PERMITIDAS

def guardar_imagen(archivo):
    if archivo and allowed_file(archivo.filename):
        filename  = secure_filename(archivo.filename)
        nombre, extension = os.path.splitext(filename)
        filename  = f"{nombre}_{int(time.time())}{extension}"
        carpeta   = os.path.join(current_app.root_path, 'static', 'images')
        os.makedirs(carpeta, exist_ok=True)
        ruta      = os.path.join(carpeta, filename)
        archivo.save(ruta)
        return url_for('static', filename=f'images/{filename}')
    return None

@products_bp.route('/')
@login_required
def list_products():
    products = Product.query.all()
    return render_template('products.html', products=products, categorias=CATEGORIAS)

@products_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_product():
    if request.method == 'POST':
        name      = request.form.get('name')
        description = request.form.get('description')
        price     = float(request.form.get('price'))
        stock     = int(request.form.get('stock'))
        categoria = request.form.get('categoria', 'juguetes')

        # Subir hasta 3 imágenes
        imagen1 = guardar_imagen(request.files.get('imagen'))
        imagen2 = guardar_imagen(request.files.get('imagen2'))
        imagen3 = guardar_imagen(request.files.get('imagen3'))

        product = Product(
            name        = name,
            description = description,
            price       = price,
            stock       = stock,
            categoria   = categoria,
            image_url   = imagen1,
            image_url2  = imagen2,
            image_url3  = imagen3,
            created_by  = current_user.id
        )
        db.session.add(product)
        db.session.commit()
        flash(f'Producto "{name}" agregado ✅', 'success')
        return redirect(url_for('products.list_products'))

    return render_template('add_product.html', product=None, categorias=CATEGORIAS)

@products_bp.route('/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)

    if request.method == 'POST':
        product.name        = request.form.get('name')
        product.price       = float(request.form.get('price'))
        product.stock       = int(request.form.get('stock'))
        product.description = request.form.get('description')
        product.categoria   = request.form.get('categoria', 'juguetes')
        product.active      = 'active' in request.form

        # Actualizar imágenes solo si se subió una nueva
        for campo, field in [('imagen', 'image_url'),
                              ('imagen2', 'image_url2'),
                              ('imagen3', 'image_url3')]:
            archivo = request.files.get(campo)
            if archivo and archivo.filename != '':
                nueva = guardar_imagen(archivo)
                if nueva:
                    setattr(product, field, nueva)

        db.session.commit()
        flash('Producto actualizado ✅', 'success')
        return redirect(url_for('products.list_products'))

    return render_template('add_product.html', product=product, categorias=CATEGORIAS)

@products_bp.route('/delete/<int:product_id>')
@login_required
def delete_product(product_id):
    if current_user.role != 'gerente':
        flash('Solo el gerente puede eliminar productos', 'error')
        return redirect(url_for('products.list_products'))

    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash('Producto eliminado', 'success')
    return redirect(url_for('products.list_products'))