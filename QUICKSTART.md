# Quick Start Guide

## Prerequisites
- Docker and Docker Compose
- Node.js 18+ (20.19+ recommended)
- Python 3.11+

## Backend Setup

1. **Start infrastructure services:**
```bash
cd autograder-back
docker-compose up -d
```

This starts:
- PostgreSQL (port 5432)
- Redis (port 6379)
- Celery worker (for async tasks)

2. **Configure environment:**
```bash
cp .env.example .env
# Edit .env and set:
# - DATABASE_URL
# - REDIS_URL
# - JWT_SECRET
# - OPENAI_API_KEY or ANTHROPIC_API_KEY (optional for LLM grading)
```

3. **Run database migrations:**
```bash
alembic upgrade head
```

4. **Start the API server:**
```bash
uvicorn app.main:app --reload
```

Backend will be available at: http://localhost:8000
API docs: http://localhost:8000/docs

## Frontend Setup

1. **Install dependencies:**
```bash
cd autograder-web
npm install
```

2. **Configure API URL (optional):**
```bash
# Create .env file
echo "VITE_API_URL=http://localhost:8000" > .env
```

3. **Start dev server:**
```bash
npm run dev
```

Frontend will be available at: http://localhost:5173

## First Run

### 1. Create a Professor Account
1. Visit http://localhost:5173
2. Click "Register"
3. Fill in:
   - Email: `prof@example.com`
   - Password: `password123`
   - Role: `Professor`
4. Click "Register"
5. You'll be redirected to login

### 2. Login
1. Enter your credentials
2. Click "Login"
3. You'll be redirected to `/professor/classes`

### 3. Create a Class
1. Click "Create Class"
2. Enter class name: `Introduction to Python`
3. Click "Create"
4. Click on the class card to view details

### 4. Invite Students
**Option A: Show invite code**
1. In class detail page, click "Show Code"
2. Copy the invite code
3. Share with students (they can use it to enroll)

**Option B: Bulk CSV import**
1. Click "Add Students (CSV)"
2. Create a CSV file:
```csv
email,name
student1@example.com,Alice
student2@example.com,Bob
```
3. Upload the file
4. Students will appear in the roster

### 5. Test Token Refresh
1. Login and navigate around
2. Open DevTools → Application → Local Storage
3. Note the `access_token` (expires in 15 min)
4. Wait or manually delete it: `localStorage.removeItem('access_token')`
5. Make a request (e.g., navigate to another page)
6. Token should auto-refresh transparently

## Testing Backend Directly

### Using curl

**Register:**
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123",
    "role": "professor"
  }'
```

**Login:**
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123"
  }'
```

Save the `access_token` from the response.

**Get current user:**
```bash
curl http://localhost:8000/users/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Create a class:**
```bash
curl -X POST http://localhost:8000/classes \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Data Science 101"}'
```

### Using Swagger UI

Visit http://localhost:8000/docs and use the interactive API documentation:
1. Click "Authorize"
2. Enter: `Bearer YOUR_ACCESS_TOKEN`
3. Test any endpoint directly in the browser

## Common Issues

### Backend won't start
- Check Docker services: `docker-compose ps`
- Check logs: `docker-compose logs -f`
- Verify DATABASE_URL is correct

### Frontend can't connect to backend
- Verify backend is running: `curl http://localhost:8000/health`
- Check VITE_API_URL in `.env`
- Check browser console for CORS errors

### Token refresh not working
- Check JWT_SECRET is set in backend .env
- Verify refresh_token is stored in localStorage
- Check backend logs for errors

### Students can't enroll
- Verify invite code is correct (case-sensitive)
- Check student is using `/login` and registering as "Student" role
- Confirm class exists and is not archived

## Next Steps

Once basic functionality is verified:
1. Try creating exercises (backend API works, UI is placeholder)
2. Test submission flow (backend works, UI is placeholder)
3. Implement remaining professor dashboard features
4. Build student dashboard
5. Add unit tests
6. Configure for production deployment

## Development Tips

### Hot Reload
- Frontend: Auto-reloads on file changes
- Backend: Use `--reload` flag with uvicorn

### Database Reset
```bash
cd autograder-back
docker-compose down -v  # Delete volumes
docker-compose up -d
alembic upgrade head
```

### View Logs
```bash
# Backend
tail -f logs/app.log

# Docker services
docker-compose logs -f

# Celery worker
docker-compose logs -f worker
```

### Environment Variables
Backend (.env):
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `JWT_SECRET`: Secret for signing JWT tokens
- `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`: For LLM grading
- `SMTP_*`: For sending password reset emails (optional)

Frontend (.env):
- `VITE_API_URL`: Backend API URL (default: http://localhost:8000)
