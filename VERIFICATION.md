# Verification Checklist

## Backend Verification

### 1. Start the backend services
```bash
cd autograder-back
docker-compose up -d  # Start PostgreSQL, Redis, Celery worker
uvicorn app.main:app --reload  # Start FastAPI server
```

### 2. Test authentication endpoints
```bash
# Register a professor
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"prof@test.com","password":"password123","role":"professor"}'

# Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"prof@test.com","password":"password123"}'

# Save the access_token from response for next steps
```

### 3. Test protected endpoints
```bash
# Get current user (requires auth)
curl http://localhost:8000/users/me \
  -H "Authorization: Bearer <access_token>"

# Create a class
curl -X POST http://localhost:8000/classes \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"name":"Introduction to Python"}'
```

### 4. Check OpenAPI docs
Visit: http://localhost:8000/docs

## Frontend Verification

### 1. Start the frontend dev server
```bash
cd autograder-web
npm run dev
```

### 2. Test authentication flow
1. Visit http://localhost:5173
2. Should redirect to /dashboard → /login (not authenticated)
3. Click "Register" and create a professor account
4. Should redirect to login after successful registration
5. Login with the credentials
6. Should redirect to /professor/classes

### 3. Test professor dashboard
1. Create a new class
2. View class details
3. Click "Show Code" to display invite code
4. Upload a CSV file with students (format: email,name)
5. Verify students appear in the roster

### 4. Test authentication persistence
1. Refresh the page → should stay logged in
2. Open DevTools → Application → Local Storage
3. Verify `access_token` and `refresh_token` are stored
4. Click Logout → should clear tokens and redirect to login

### 5. Test token refresh (optional)
1. In DevTools Console, run:
```javascript
// Wait for access token to expire (15 min) or manually delete it
localStorage.removeItem('access_token');
// Make an API request - should auto-refresh
```

## Known Limitations (Expected)

- **Frontend incomplete:** Exercise management, grades view, and student dashboard are placeholders
- **No real email:** Password reset emails won't send without SMTP configuration
- **Sandbox execution:** Requires Docker daemon running for code execution
- **LLM grading:** Requires OpenAI/Anthropic API key in environment variables

## Next Steps After Verification

If everything works:
1. Continue with remaining professor dashboard features (exercises, grades)
2. Implement student dashboard
3. Add unit tests
4. Prepare for deployment

If issues found:
- Document the error
- Check backend logs: `docker-compose logs -f`
- Check browser console for frontend errors
- Verify environment variables are set correctly
