"""
Seed script: cadastra os produtos Hotmart e suas ProductAccessRules no banco.

Uso:
    uv run python seed_products.py

Idempotente: usa upsert por hotmart_product_id.
"""
from app.database import SessionLocal
from app.models.product import Product, ProductAccessRule, AccessRuleType

PRODUCTS = [
    {
        "name": "O Senhor das LLMs",
        "hotmart_product_id": "4141338",
        "tags": ["Senhor das LLMs"],
    },
    {
        "name": "De analista a CDO",
        "hotmart_product_id": "6207530",
        "tags": ["De analista a CDO"],
    },
    {
        "name": "A Base de Tudo",
        "hotmart_product_id": "6626505",
        # Grants access to its own tag AND to CDO content
        "tags": ["A Base de Tudo", "De analista a CDO"],
    },
    {
        "name": "Do Zero à Analista",
        "hotmart_product_id": "7143204",
        "tags": ["Do Zero à Analista"],
    },
    {
        "name": "Como Estudar",
        "hotmart_product_id": "6624021",
        "tags": ["Como Estudar"],
    },
]

db = SessionLocal()
try:
    for p in PRODUCTS:
        product = db.query(Product).filter(
            Product.hotmart_product_id == p["hotmart_product_id"]
        ).first()

        if not product:
            product = Product(
                name=p["name"],
                hotmart_product_id=p["hotmart_product_id"],
                is_active=True,
            )
            db.add(product)
            db.flush()
            print(f"  Created: {p['name']}")
        else:
            print(f"  Exists:  {p['name']}")

        # Ensure MANYCHAT_TAG rules exist
        existing_tags = {r.rule_value for r in product.access_rules
                         if r.rule_type == AccessRuleType.MANYCHAT_TAG}
        for tag in p["tags"]:
            if tag not in existing_tags:
                db.add(ProductAccessRule(
                    product_id=product.id,
                    rule_type=AccessRuleType.MANYCHAT_TAG,
                    rule_value=tag,
                ))
                print(f"    + tag rule: {tag}")

    db.commit()
    print("\nDone.")
finally:
    db.close()
