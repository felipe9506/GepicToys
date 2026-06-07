from app import create_app
from models import db, Product

app = create_app()

productos = [
    {
        "name": "Naruto Uzumaki - Modo Sabio",
        "description": "Figura articulada 30cm con base especial. Edición limitada.",
        "price": 44.900,
        "stock": 15,
        "image_url": "https://cdn.shopify.com/s/files/1/0551/9261/4081/files/naruto-sage-mode.jpg"
    },
    {
        "name": "Goku Ultra Instinto",
        "description": "Figura Dragon Ball Super 25cm con aura de ki iluminada.",
        "price": 29.000,
        "stock": 10,
        "image_url": "https://images-na.ssl-images-amazon.com/images/I/61y1tAzpGiL.jpg"
    },
    {
        "name": "Demon Slayer - Tanjiro Kamado",
        "description": "Figura Kimetsu no Yaiba 28cm con espada Nichirin incluida.",
        "price": 27.000,
        "stock": 8,
        "image_url": "https://i.ebayimg.com/images/g/various/s-l1600.jpg"
    },
    {
        "name": "Monkey D. Luffy - Gear 5",
        "description": "Figura One Piece 32cm edición Gear Fifth con efectos.",
        "price": 34.900,
        "stock": 12,
        "image_url": "https://ae01.alicdn.com/kf/luffy-gear5.jpg"
    },
    {
        "name": "Levi Ackerman - SNK",
        "description": "Figura Attack on Titan 22cm con equipo de maniobra 3D.",
        "price": 22.900,
        "stock": 20,
        "image_url": "https://ae01.alicdn.com/kf/levi-snk.jpg"
    },
    {
        "name": "Zero Two - Darling in the FranXX",
        "description": "Figura 26cm con traje de piloto y detalles premium.",
        "price": 31.900,
        "stock": 6,
        "image_url": "https://ae01.alicdn.com/kf/zerotwo.jpg"
    },
]

with app.app_context():
    # Actualizar URLs de los productos existentes
    for p in productos:
        producto = Product.query.filter_by(name=p['name']).first()
        if producto:
            producto.image_url = p['image_url']
        else:
            db.session.add(Product(
                name=p['name'],
                description=p['description'],
                price=p['price'],
                stock=p['stock'],
                image_url=p['image_url'],
                active=True,
                created_by=2
            ))
    db.session.commit()
    print("✅ URLs actualizadas")