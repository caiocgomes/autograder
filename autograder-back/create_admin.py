from app.database import SessionLocal
from app.models.user import User, UserRole
from app.auth.security import hash_password

db = SessionLocal()
user = User(email='caio@caiogomes.com.br', password_hash=hash_password('ca49ci'), role=UserRole.ADMIN)
db.add(user)
db.commit()
print(f'Admin criado: id={user.id}')
db.close()
