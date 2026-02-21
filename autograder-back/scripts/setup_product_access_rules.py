"""
Script de setup: produtos e product → Discord role mappings

Operações (idempotente — pode rodar várias vezes):
1. Upsert dos 6 produtos de produção
2. Criar as ProductAccessRules se ainda não existirem

Uso: python scripts/setup_product_access_rules.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.product import Product, ProductAccessRule, AccessRuleType
from app.config import settings

engine = create_engine(settings.database_url)
Session = sessionmaker(bind=engine)


PRODUCTS = [
    {"name": "O Senhor das LLMs",                      "hotmart_product_id": "4141338"},
    {"name": "De analista a CDO",                      "hotmart_product_id": "6207530"},
    {"name": "A Base de Tudo",                         "hotmart_product_id": "6626505"},
    {"name": "Do Zero à Analista",                     "hotmart_product_id": "7143204"},
    {"name": "Como Estudar",                           "hotmart_product_id": "6624021"},
    {"name": "Acelerando sua inovação com teste A/B",  "hotmart_product_id": "5231742"},
]

# (hotmart_product_id, discord_role_id, descricao)
RULES = [
    ("4141338", "1449458468057518323", "O Senhor das LLMs → O Senhor das LLMs"),
    ("6207530", "1449458402941210870", "De analista a CDO → De Analista a CDO"),
    ("6626505", "1449458468057518323", "A Base de Tudo → O Senhor das LLMs"),
    ("6626505", "1449458614736519341", "A Base de Tudo → Como Estudar?"),
    ("6626505", "1449458402941210870", "A Base de Tudo → De Analista a CDO"),
    ("7143204", "1474822529658130462", "Do Zero à Analista → De Zero a Analista"),
    ("6624021", "1449458614736519341", "Como Estudar → Como Estudar?"),
    ("5231742", "1449458514350051399", "A/B Testing → Acelerando com A/B Testing"),
]


def upsert_products(db):
    print("\n=== PRODUTOS ===")
    product_map = {}  # hotmart_product_id -> Product

    for p in PRODUCTS:
        existing = db.query(Product).filter(
            Product.hotmart_product_id == p["hotmart_product_id"]
        ).first()

        if existing:
            print(f"  SKIP (já existe id={existing.id}): {p['name']!r}")
            product_map[p["hotmart_product_id"]] = existing
        else:
            product = Product(name=p["name"], hotmart_product_id=p["hotmart_product_id"], is_active=True)
            db.add(product)
            db.flush()
            print(f"  CRIADO id={product.id}: {p['name']!r}")
            product_map[p["hotmart_product_id"]] = product

    return product_map


def upsert_rules(db, product_map):
    print("\n=== PRODUCTACCESSRULES ===")

    for hotmart_id, role_id, descricao in RULES:
        product = product_map.get(hotmart_id)
        if not product:
            print(f"  SKIP (produto {hotmart_id} não encontrado): {descricao}")
            continue

        existing = db.query(ProductAccessRule).filter(
            ProductAccessRule.product_id == product.id,
            ProductAccessRule.rule_type == AccessRuleType.DISCORD_ROLE,
            ProductAccessRule.rule_value == role_id,
        ).first()

        if existing:
            print(f"  SKIP (já existe id={existing.id}): {descricao}")
            continue

        rule = ProductAccessRule(
            product_id=product.id,
            rule_type=AccessRuleType.DISCORD_ROLE,
            rule_value=role_id,
        )
        db.add(rule)
        db.flush()
        print(f"  CRIADO id={rule.id}: {descricao}")


def verify(db):
    print("\n=== VERIFICAÇÃO FINAL ===")
    products = db.query(Product).order_by(Product.id).all()
    for p in products:
        rules = db.query(ProductAccessRule).filter(ProductAccessRule.product_id == p.id).all()
        print(f"\n  id={p.id} | {p.name!r} | hotmart={p.hotmart_product_id}")
        for r in rules:
            print(f"    Rule id={r.id}: {r.rule_type.value} = {r.rule_value}")
        if not rules:
            print("    (sem regras)")


def main():
    db = Session()
    try:
        product_map = upsert_products(db)
        upsert_rules(db, product_map)
        db.commit()
        print("\n[OK] Commit realizado.")
        verify(db)
    except Exception as e:
        db.rollback()
        print(f"\n[ERRO] Rollback. {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
