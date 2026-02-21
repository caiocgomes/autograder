"""Tests for onboard_historical_buyers Celery task."""
import pytest
from unittest.mock import Mock, MagicMock, patch, call

from app.models.hotmart_buyer import HotmartBuyer
from app.models.user import User, UserRole, LifecycleStatus


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.query.return_value = db
    db.filter.return_value = db
    db.first.return_value = None
    db.all.return_value = []
    return db


def make_buyer(email, name="Test User", phone="+5511999990000", product_id="prod_123", user_id=None):
    b = Mock(spec=HotmartBuyer)
    b.email = email
    b.name = name
    b.phone = phone
    b.hotmart_product_id = product_id
    b.user_id = user_id
    b.status = "Ativo"
    return b


class TestOnboardHistoricalBuyers:

    def test_buyer_ativo_sem_conta_cria_user_com_campos_corretos(self, mock_db):
        """Buyer ativo sem User → User criado com email, name e whatsapp_number."""
        buyer = make_buyer("joao@test.com", name="João Silva", phone="+5511999990000")
        mock_db.all.return_value = [buyer]
        mock_db.first.return_value = None  # User não existe

        created_users = []
        original_add = mock_db.add.side_effect

        def capture_add(obj):
            if isinstance(obj, User):
                created_users.append(obj)

        mock_db.add.side_effect = capture_add

        with patch("app.tasks.SessionLocal", return_value=mock_db):
            with patch("app.services.lifecycle.transition") as mock_transition:
                mock_transition.return_value = LifecycleStatus.PENDING_ONBOARDING
                from app.tasks import onboard_historical_buyers
                result = onboard_historical_buyers.run()

        assert result["created"] == 1
        assert result["total"] == 1
        assert len(created_users) == 1
        u = created_users[0]
        assert u.email == "joao@test.com"
        assert u.whatsapp_number == "+5511999990000"
        assert u.role == UserRole.STUDENT
        assert u.lifecycle_status is None

    def test_buyer_com_phone_chama_transition(self, mock_db):
        """Buyer com phone → lifecycle.transition chamado com trigger correto."""
        buyer = make_buyer("aluno@test.com", phone="+5511888880000", product_id="prod_abc")
        mock_db.all.return_value = [buyer]
        mock_db.first.return_value = None

        with patch("app.tasks.SessionLocal", return_value=mock_db):
            with patch("app.services.lifecycle.transition") as mock_transition:
                mock_transition.return_value = LifecycleStatus.PENDING_ONBOARDING
                from app.tasks import onboard_historical_buyers
                result = onboard_historical_buyers.run()

        mock_transition.assert_called_once()
        call_kwargs = mock_transition.call_args
        assert call_kwargs.kwargs["trigger"] == "purchase_approved"
        assert call_kwargs.kwargs["hotmart_product_id"] == "prod_abc"
        assert result["created"] == 1

    def test_buyer_sem_phone_cria_user_sem_whatsapp(self, mock_db):
        """Buyer sem phone → User criado com whatsapp_number=None, transition chamado."""
        buyer = make_buyer("semphone@test.com", phone=None)
        mock_db.all.return_value = [buyer]
        mock_db.first.return_value = None

        created_users = []

        def capture_add(obj):
            if isinstance(obj, User):
                created_users.append(obj)

        mock_db.add.side_effect = capture_add

        with patch("app.tasks.SessionLocal", return_value=mock_db):
            with patch("app.services.lifecycle.transition") as mock_transition:
                mock_transition.return_value = LifecycleStatus.PENDING_ONBOARDING
                from app.tasks import onboard_historical_buyers
                result = onboard_historical_buyers.run()

        assert result["created"] == 1
        assert len(created_users) == 1
        assert created_users[0].whatsapp_number is None
        mock_transition.assert_called_once()

    def test_comprador_com_dois_produtos_cria_um_user(self, mock_db):
        """Email com dois produtos → um User criado, dois rows user_id atualizados."""
        buyer1 = make_buyer("multi@test.com", product_id="prod_1")
        buyer2 = make_buyer("multi@test.com", product_id="prod_2")
        mock_db.all.return_value = [buyer1, buyer2]
        mock_db.first.return_value = None

        created_users = []

        def capture_add(obj):
            if isinstance(obj, User):
                created_users.append(obj)

        mock_db.add.side_effect = capture_add

        with patch("app.tasks.SessionLocal", return_value=mock_db):
            with patch("app.services.lifecycle.transition") as mock_transition:
                mock_transition.return_value = LifecycleStatus.PENDING_ONBOARDING
                from app.tasks import onboard_historical_buyers
                result = onboard_historical_buyers.run()

        assert result["created"] == 1
        assert result["total"] == 1
        assert len(created_users) == 1
        # transition só é chamado uma vez
        mock_transition.assert_called_once()

    def test_reexecucao_com_user_id_ja_preenchido_nao_processa(self, mock_db):
        """Rows com user_id preenchido → all() retorna vazio → created=0."""
        mock_db.all.return_value = []  # query filtra user_id IS NULL

        with patch("app.tasks.SessionLocal", return_value=mock_db):
            with patch("app.services.lifecycle.transition") as mock_transition:
                from app.tasks import onboard_historical_buyers
                result = onboard_historical_buyers.run()

        assert result["created"] == 0
        assert result["total"] == 0
        mock_transition.assert_not_called()

    def test_email_ja_existe_em_users_faz_skip(self, mock_db):
        """Email já tem User → vincula user_id, skipped=1, sem criar duplicata."""
        buyer = make_buyer("existente@test.com")
        existing_user = Mock(spec=User)
        existing_user.id = 99

        mock_db.all.return_value = [buyer]
        mock_db.first.return_value = existing_user  # User encontrado

        created_users = []

        def capture_add(obj):
            if isinstance(obj, User):
                created_users.append(obj)

        mock_db.add.side_effect = capture_add

        with patch("app.tasks.SessionLocal", return_value=mock_db):
            with patch("app.services.lifecycle.transition") as mock_transition:
                from app.tasks import onboard_historical_buyers
                result = onboard_historical_buyers.run()

        assert result["skipped"] == 1
        assert result["created"] == 0
        assert len(created_users) == 0
        mock_transition.assert_not_called()
        assert buyer.user_id == 99

    def test_falha_em_um_buyer_nao_aborta_outros(self, mock_db):
        """Falha no processamento de um buyer → errors=1, próximo é processado."""
        buyer1 = make_buyer("falha@test.com")
        buyer2 = make_buyer("ok@test.com")
        mock_db.all.return_value = [buyer1, buyer2]

        call_count = 0

        def first_side_effect():
            nonlocal call_count
            call_count += 1
            return None

        mock_db.first.return_value = None

        def transition_side_effect(db, user, trigger, hotmart_product_id=None, actor_id=None):
            if user.email == "falha@test.com":
                raise Exception("Evolution timeout")
            return LifecycleStatus.PENDING_ONBOARDING

        created_users = []

        def capture_add(obj):
            if isinstance(obj, User):
                created_users.append(obj)

        mock_db.add.side_effect = capture_add

        with patch("app.tasks.SessionLocal", return_value=mock_db):
            with patch("app.services.lifecycle.transition", side_effect=transition_side_effect):
                from app.tasks import onboard_historical_buyers
                result = onboard_historical_buyers.run()

        assert result["errors"] == 1
        assert result["created"] == 1
        assert result["total"] == 2

    def test_counters_e_evento_registrado(self, mock_db):
        """Task retorna counters corretos e registra Event ao final."""
        buyer = make_buyer("aluno@test.com")
        mock_db.all.return_value = [buyer]
        mock_db.first.return_value = None

        added_objects = []

        def capture_add(obj):
            added_objects.append(obj)

        mock_db.add.side_effect = capture_add

        with patch("app.tasks.SessionLocal", return_value=mock_db):
            with patch("app.services.lifecycle.transition") as mock_transition:
                mock_transition.return_value = LifecycleStatus.PENDING_ONBOARDING
                from app.tasks import onboard_historical_buyers
                result = onboard_historical_buyers.run()

        assert "created" in result
        assert "skipped" in result
        assert "errors" in result
        assert "total" in result

        from app.models.event import Event
        events = [o for o in added_objects if isinstance(o, Event)]
        assert any(
            getattr(e, "type", None) == "hotmart_buyers.historical_onboarding_completed"
            for e in events
        )
