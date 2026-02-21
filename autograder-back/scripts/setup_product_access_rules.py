"""
Script de setup: product → Discord role mappings

Operações:
1. Limpar dados de teste (Caetano + produto de teste)
2. Criar 7 ProductAccessRules de produção

Uso: uv run python scripts/setup_product_access_rules.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.models.product import ProductAccessRule, AccessRuleType
from app.models.user import User
from app.config import settings

engine = create_engine(settings.database_url)
Session = sessionmaker(bind=engine)


def cleanup_test_data(db):
    print("\n=== LIMPEZA DE DADOS DE TESTE ===")

    # 1. Reset Caetano
    caetano = db.query(User).filter(User.email == "caetanosrc@gmail.com").first()
    if caetano:
        print(f"Caetano encontrado (id={caetano.id})")
        print(f"  Antes: discord_id={caetano.discord_id}, lifecycle_status={caetano.lifecycle_status}, onboarding_token={caetano.onboarding_token}")
        caetano.discord_id = None
        caetano.lifecycle_status = None
        caetano.onboarding_token = None
        caetano.onboarding_token_expires_at = None
        db.flush()
        print(f"  Depois: discord_id=None, lifecycle_status=None, onboarding_token=None")
    else:
        print("Caetano não encontrado — nada a resetar")

    # 2. Deletar ProductAccessRule id=7
    rule = db.query(ProductAccessRule).filter(ProductAccessRule.id == 7).first()
    if rule:
        print(f"\nDeletando ProductAccessRule id=7 (product_id={rule.product_id}, value={rule.rule_value})")
        db.delete(rule)
        db.flush()
        print("  Deletado.")
    else:
        print("\nProductAccessRule id=7 não encontrada — nada a deletar")

    # 3. Deletar Product id=6
    from app.models.product import Product
    product = db.query(Product).filter(Product.id == 6).first()
    if product:
        print(f"\nDeletando Product id=6 (name={product.name!r}, hotmart_id={product.hotmart_product_id!r})")
        db.delete(product)
        db.flush()
        print("  Deletado.")
    else:
        print("\nProduct id=6 não encontrado — nada a deletar")


def create_access_rules(db):
    print("\n=== CRIANDO PRODUCTACCESSRULES DE PRODUÇÃO ===")

    rules_to_create = [
        # (product_id, discord_role_id, descricao)
        (1, "1449458468057518323", "O Senhor das LLMs → O Senhor das LLMs"),
        (2, "1449458402941210870", "De analista a CDO → De Analista a CDO"),
        (3, "1449458468057518323", "A Base de Tudo → O Senhor das LLMs"),
        (3, "1449458614736519341", "A Base de Tudo → Como Estudar?"),
        (3, "1449458402941210870", "A Base de Tudo → De Analista a CDO"),
        (4, "1474822529658130462", "Do Zero à Analista → De Zero a Analista"),
        (5, "1449458614736519341", "Como Estudar → Como Estudar?"),
    ]

    for product_id, role_id, descricao in rules_to_create:
        # Verificar se já existe
        existing = db.query(ProductAccessRule).filter(
            ProductAccessRule.product_id == product_id,
            ProductAccessRule.rule_type == AccessRuleType.DISCORD_ROLE,
            ProductAccessRule.rule_value == role_id,
        ).first()

        if existing:
            print(f"  SKIP (já existe id={existing.id}): {descricao}")
            continue

        rule = ProductAccessRule(
            product_id=product_id,
            rule_type=AccessRuleType.DISCORD_ROLE,
            rule_value=role_id,
        )
        db.add(rule)
        db.flush()
        print(f"  CRIADO id={rule.id}: {descricao}")


def verify(db):
    print("\n=== VERIFICAÇÃO FINAL ===")

    print("\nProductAccessRules por produto:")
    from app.models.product import Product
    products = db.query(Product).order_by(Product.id).all()
    for p in products:
        rules = db.query(ProductAccessRule).filter(ProductAccessRule.product_id == p.id).all()
        print(f"\n  Produto id={p.id} | {p.name!r} | hotmart={p.hotmart_product_id}")
        if rules:
            for r in rules:
                print(f"    Rule id={r.id}: {r.rule_type.value} = {r.rule_value}")
        else:
            print("    (sem regras)")

    print("\nCaetano:")
    caetano = db.query(User).filter(User.email == "caetanosrc@gmail.com").first()
    if caetano:
        print(f"  discord_id={caetano.discord_id}")
        print(f"  lifecycle_status={caetano.lifecycle_status}")
        print(f"  onboarding_token={caetano.onboarding_token}")
    else:
        print("  não encontrado")


def main():
    db = Session()
    try:
        cleanup_test_data(db)
        create_access_rules(db)
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
