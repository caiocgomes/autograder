"""Tests for sync_hotmart_buyers Celery task."""
import pytest
from unittest.mock import Mock, MagicMock, patch

from app.models.hotmart_buyer import HotmartBuyer
from app.models.user import User


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.query.return_value = db
    db.filter.return_value = db
    db.first.return_value = None
    db.all.return_value = []
    return db


@pytest.fixture
def mock_product():
    product = Mock()
    product.id = 1
    product.hotmart_product_id = "hotmart_prod_123"
    product.is_active = True
    return product


CONTACT_INFO = [{"email": "comprador@test.com", "name": "João Silva", "phone": "+5511999990000"}]


class TestSyncHotmartBuyers:

    def test_buyer_sem_conta_inserido_com_user_id_null(self, mock_db, mock_product):
        """Comprador sem conta na plataforma → user_id = NULL na inserção."""
        mock_db.all.return_value = [mock_product]
        mock_db.first.side_effect = [None, None]  # user lookup, buyer lookup

        with patch("app.tasks.SessionLocal", return_value=mock_db):
            with patch("app.integrations.hotmart.get_buyer_statuses",
                       return_value={"comprador@test.com": "Ativo"}):
                with patch("app.integrations.hotmart.list_buyers_with_phone", return_value=iter([])):
                    from app.tasks import sync_hotmart_buyers
                    result = sync_hotmart_buyers.run()

        assert result["inserted"] == 1
        assert result["updated"] == 0
        assert result["total"] == 1
        assert result["errors"] == 0

        add_calls = mock_db.add.call_args_list
        buyer_adds = [c[0][0] for c in add_calls if isinstance(c[0][0], HotmartBuyer)]
        assert len(buyer_adds) == 1
        assert buyer_adds[0].user_id is None

    def test_buyer_com_conta_tem_user_id_preenchido(self, mock_db, mock_product):
        """Comprador com email igual a um User existente → user_id preenchido."""
        existing_user = Mock(spec=User)
        existing_user.id = 42
        existing_user.email = "aluno@test.com"

        mock_db.all.return_value = [mock_product]
        mock_db.first.side_effect = [existing_user, None]

        with patch("app.tasks.SessionLocal", return_value=mock_db):
            with patch("app.integrations.hotmart.get_buyer_statuses",
                       return_value={"aluno@test.com": "Ativo"}):
                with patch("app.integrations.hotmart.list_buyers_with_phone", return_value=iter([])):
                    from app.tasks import sync_hotmart_buyers
                    result = sync_hotmart_buyers.run()

        assert result["inserted"] == 1
        assert result["total"] == 1

        add_calls = mock_db.add.call_args_list
        buyer_adds = [c[0][0] for c in add_calls if isinstance(c[0][0], HotmartBuyer)]
        assert len(buyer_adds) == 1
        assert buyer_adds[0].user_id == 42

    def test_resync_atualiza_status_sem_duplicata(self, mock_db, mock_product):
        """Re-sync do mesmo buyer atualiza status e last_synced_at, sem inserir nova linha."""
        existing_buyer = Mock(spec=HotmartBuyer)
        existing_buyer.status = "Ativo"
        existing_buyer.user_id = None
        existing_buyer.last_synced_at = None

        mock_db.all.return_value = [mock_product]
        mock_db.first.side_effect = [None, existing_buyer]

        with patch("app.tasks.SessionLocal", return_value=mock_db):
            with patch("app.integrations.hotmart.get_buyer_statuses",
                       return_value={"aluno@test.com": "Inadimplente"}):
                with patch("app.integrations.hotmart.list_buyers_with_phone", return_value=iter([])):
                    from app.tasks import sync_hotmart_buyers
                    result = sync_hotmart_buyers.run()

        assert result["updated"] == 1
        assert result["inserted"] == 0
        assert result["total"] == 1
        assert existing_buyer.status == "Inadimplente"
        assert existing_buyer.last_synced_at is not None

    def test_falha_api_um_produto_nao_aborta_outros(self, mock_db):
        """Falha na API para um produto não interrompe o processamento dos demais."""
        product_1 = Mock()
        product_1.id = 1
        product_1.hotmart_product_id = "prod_fail"

        product_2 = Mock()
        product_2.id = 2
        product_2.hotmart_product_id = "prod_ok"

        mock_db.all.return_value = [product_1, product_2]
        mock_db.first.side_effect = [None, None]

        def api_side_effect(pid):
            if pid == "prod_fail":
                raise Exception("API timeout")
            return {"aluno@test.com": "Ativo"}

        with patch("app.tasks.SessionLocal", return_value=mock_db):
            with patch("app.integrations.hotmart.get_buyer_statuses",
                       side_effect=api_side_effect):
                with patch("app.integrations.hotmart.list_buyers_with_phone", return_value=iter([])):
                    from app.tasks import sync_hotmart_buyers
                    result = sync_hotmart_buyers.run()

        assert result["errors"] == 1
        assert result["total"] == 1
        assert result["inserted"] == 1

    def test_name_e_phone_populados_na_insercao(self, mock_db, mock_product):
        """Buyer novo recebe name e phone do /sales/users quando disponível."""
        mock_db.all.return_value = [mock_product]
        mock_db.first.side_effect = [None, None]  # user lookup, buyer lookup

        with patch("app.tasks.SessionLocal", return_value=mock_db):
            with patch("app.integrations.hotmart.get_buyer_statuses",
                       return_value={"comprador@test.com": "Ativo"}):
                with patch("app.integrations.hotmart.list_buyers_with_phone",
                           return_value=iter(CONTACT_INFO)):
                    from app.tasks import sync_hotmart_buyers
                    result = sync_hotmart_buyers.run()

        assert result["inserted"] == 1

        add_calls = mock_db.add.call_args_list
        buyer_adds = [c[0][0] for c in add_calls if isinstance(c[0][0], HotmartBuyer)]
        assert len(buyer_adds) == 1
        assert buyer_adds[0].name == "João Silva"
        assert buyer_adds[0].phone == "+5511999990000"

    def test_name_e_phone_atualizados_no_resync(self, mock_db, mock_product):
        """Re-sync atualiza name e phone quando contact_info retorna dados."""
        existing_buyer = Mock(spec=HotmartBuyer)
        existing_buyer.status = "Ativo"
        existing_buyer.user_id = None
        existing_buyer.last_synced_at = None
        existing_buyer.name = None
        existing_buyer.phone = None

        mock_db.all.return_value = [mock_product]
        mock_db.first.side_effect = [None, existing_buyer]

        with patch("app.tasks.SessionLocal", return_value=mock_db):
            with patch("app.integrations.hotmart.get_buyer_statuses",
                       return_value={"comprador@test.com": "Ativo"}):
                with patch("app.integrations.hotmart.list_buyers_with_phone",
                           return_value=iter(CONTACT_INFO)):
                    from app.tasks import sync_hotmart_buyers
                    result = sync_hotmart_buyers.run()

        assert result["updated"] == 1
        assert existing_buyer.name == "João Silva"
        assert existing_buyer.phone == "+5511999990000"

    def test_buyer_sem_contato_no_sales_users_fica_sem_name_phone(self, mock_db, mock_product):
        """Buyer histórico sem dados no /sales/users → name e phone permanecem None."""
        mock_db.all.return_value = [mock_product]
        mock_db.first.side_effect = [None, None]

        with patch("app.tasks.SessionLocal", return_value=mock_db):
            with patch("app.integrations.hotmart.get_buyer_statuses",
                       return_value={"antigo@test.com": "Cancelado"}):
                with patch("app.integrations.hotmart.list_buyers_with_phone", return_value=iter([])):
                    from app.tasks import sync_hotmart_buyers
                    result = sync_hotmart_buyers.run()

        add_calls = mock_db.add.call_args_list
        buyer_adds = [c[0][0] for c in add_calls if isinstance(c[0][0], HotmartBuyer)]
        assert len(buyer_adds) == 1
        assert buyer_adds[0].name is None
        assert buyer_adds[0].phone is None

    def test_falha_em_list_buyers_with_phone_nao_aborta_sync(self, mock_db, mock_product):
        """Falha no /sales/users não aborta o sync — processa sem contact info."""
        mock_db.all.return_value = [mock_product]
        mock_db.first.side_effect = [None, None]

        with patch("app.tasks.SessionLocal", return_value=mock_db):
            with patch("app.integrations.hotmart.get_buyer_statuses",
                       return_value={"comprador@test.com": "Ativo"}):
                with patch("app.integrations.hotmart.list_buyers_with_phone",
                           side_effect=Exception("timeout")):
                    from app.tasks import sync_hotmart_buyers
                    result = sync_hotmart_buyers.run()

        assert result["inserted"] == 1
        assert result["errors"] == 0
