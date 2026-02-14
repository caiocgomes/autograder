## 1. Infrastructure Setup

- [x] 1.1 Setup PostgreSQL database schema with Alembic migrations
- [x] 1.2 Configure Redis for caching and task queue
- [x] 1.3 Setup Celery workers for async task processing
- [x] 1.4 Create Docker Compose config for dev environment (app, db, redis, worker)
- [x] 1.5 Configure Docker base image for Python sandbox execution
- [x] 1.6 Setup environment variables and secrets management

## 2. Database Models (Backend)

- [x] 2.1 Create User model (id, email, password_hash, role, created_at)
- [x] 2.2 Create Class model (id, name, professor_id FK, archived, created_at)
- [x] 2.3 Create ClassEnrollment model (id, class_id FK, student_id FK, enrolled_at)
- [x] 2.4 Create Group and GroupMembership models
- [x] 2.5 Create Exercise model (id, title, description, template_code, language, constraints)
- [x] 2.6 Create ExerciseList and ExerciseListItem models
- [x] 2.7 Create Submission model (id, exercise_id FK, student_id FK, code, status, submitted_at)
- [x] 2.8 Create TestResult model (id, submission_id FK, test_name, passed, message)
- [x] 2.9 Create LLMEvaluation model (id, submission_id FK, feedback, score, cached, created_at)
- [x] 2.10 Create Grade model (id, submission_id FK unique, test_score, llm_score, final_score, published)
- [x] 2.11 Create database indexes for performance (class_enrollments, submissions, llm_evaluations)
- [x] 2.12 Run initial Alembic migration

## 3. Backend - User Authentication

- [x] 3.1 Implement password hashing with bcrypt (cost factor 12)
- [x] 3.2 Create POST /auth/register endpoint with email validation
- [x] 3.3 Create POST /auth/login endpoint returning JWT access + refresh tokens
- [x] 3.4 Implement JWT token generation (access 15min, refresh 7 days)
- [x] 3.5 Create POST /auth/refresh endpoint for token renewal
- [x] 3.6 Create POST /auth/password-reset endpoint sending email with reset token
- [x] 3.7 Create POST /auth/password-reset/confirm endpoint to complete reset
- [x] 3.8 Implement rate limiting middleware (5 failed logins per 15 min)
- [x] 3.9 Create JWT authentication middleware for protected routes
- [x] 3.10 Implement RBAC middleware checking user roles (admin, professor, student, ta)

## 4. Backend - User Management

- [x] 4.1 Create GET /users/me endpoint returning current user profile
- [x] 4.2 Create PATCH /users/me endpoint for profile updates (email, password)
- [x] 4.3 Create GET /users endpoint (admin only) for user listing
- [x] 4.4 Implement email verification flow for email changes

## 5. Backend - Class Management

- [x] 5.1 Create POST /classes endpoint (professor creates class)
- [x] 5.2 Generate unique invite codes per class on creation
- [x] 5.3 Create GET /classes endpoint listing user's classes (filter by role)
- [x] 5.4 Create GET /classes/{id} endpoint with class details and roster
- [x] 5.5 Create POST /classes/{id}/enroll endpoint for student enrollment via invite code
- [x] 5.6 Create POST /classes/{id}/students endpoint for bulk CSV import
- [x] 5.7 Implement CSV parser validating email/name columns
- [x] 5.8 Create DELETE /classes/{id}/students/{student_id} endpoint to unenroll student
- [x] 5.9 Create POST /classes/{id}/groups endpoint to create groups
- [x] 5.10 Create POST /groups/{id}/members endpoint to assign students to groups
- [x] 5.11 Create PATCH /classes/{id}/archive endpoint to archive class

## 6. Backend - Exercise Creation

- [x] 6.1 Create POST /exercises endpoint with Markdown description support
- [x] 6.2 Implement file upload for datasets (max 10MB, store in S3 or local filesystem)
- [x] 6.3 Create PATCH /exercises/{id} endpoint for exercise updates
- [x] 6.4 Create GET /exercises endpoint with filtering (by professor, tags, published)
- [x] 6.5 Create GET /exercises/{id} endpoint returning full exercise details
- [x] 6.6 Implement template code storage and retrieval
- [x] 6.7 Create POST /exercises/{id}/tests endpoint to add test cases
- [x] 6.8 Implement test case storage (input, expected output, hidden flag)
- [x] 6.9 Create exercise visibility toggle (draft vs published)
- [x] 6.10 Implement tagging system for exercises

## 7. Backend - Exercise Lists

- [x] 7.1 Create POST /exercise-lists endpoint to create list
- [x] 7.2 Create POST /exercise-lists/{id}/exercises endpoint to add exercises with weight/position
- [x] 7.3 Create PATCH /exercise-lists/{id}/exercises/{exercise_id} endpoint to reorder exercises
- [x] 7.4 Create DELETE /exercise-lists/{id}/exercises/{exercise_id} endpoint with submission check
- [x] 7.5 Create GET /classes/{class_id}/lists endpoint listing lists for class
- [x] 7.6 Implement date-based visibility (opens_at, closes_at)
- [x] 7.7 Implement group-specific list assignment
- [ ] 7.8 Create exercise randomization logic per student (optional)
- [x] 7.9 Implement late penalty calculation (percent per day)

## 8. Backend - Code Submission

- [x] 8.1 Create POST /submissions endpoint accepting file upload or code text
- [x] 8.2 Implement file validation (extension, size limit 1MB)
- [x] 8.3 Implement basic Python syntax validation before enqueue
- [x] 8.4 Enforce submission limits per exercise
- [x] 8.5 Enforce deadline checks (reject or apply late penalty)
- [x] 8.6 Create submission record with status "queued"
- [x] 8.7 Enqueue submission task to Celery
- [x] 8.8 Create GET /submissions endpoint with filtering (exercise_id, student_id)
- [x] 8.9 Create GET /submissions/{id} endpoint returning submission details
- [x] 8.10 Create GET /submissions/{id}/results endpoint returning test results and feedback
- [x] 8.11 Implement submission status polling endpoint
- [x] 8.12 Create diff utility for comparing submissions

## 9. Backend - Sandboxed Execution

- [x] 9.1 Create Celery task for code execution
- [x] 9.2 Implement Docker container creation with resource limits (1 core, 512MB memory)
- [x] 9.3 Configure container network isolation (network mode: none)
- [x] 9.4 Configure container filesystem (read-only except /tmp)
- [x] 9.5 Implement container security hardening (drop capabilities, non-root user)
- [x] 9.6 Mount student code and datasets into container
- [x] 9.7 Mount test harness into container
- [x] 9.8 Execute tests inside container with timeout enforcement
- [x] 9.9 Capture stdout, stderr, exit code from container
- [x] 9.10 Implement output truncation (max 100KB)
- [x] 9.11 Destroy container after execution
- [x] 9.12 Parse test results and save to TestResult table
- [x] 9.13 Implement retry logic for infrastructure failures (max 3 retries)
- [x] 9.14 Update submission status (running -> completed/failed)

## 10. Backend - Automated Grading

- [x] 10.1 Calculate test score as (passed / total) percentage
- [x] 10.2 Implement LLM grading task (conditional on llm_grading_enabled)
- [x] 10.3 Create LLM prompt template (exercise description + code + criteria)
- [x] 10.4 Integrate OpenAI or Anthropic API for LLM calls
- [x] 10.5 Parse LLM response to extract feedback text and score
- [x] 10.6 Implement LLM response caching by code hash
- [x] 10.7 Implement composite score calculation (test_weight * test_score + llm_weight * llm_score)
- [x] 10.8 Create Grade record with final score
- [x] 10.9 Implement auto-publish vs manual review logic
- [x] 10.10 Create POST /grades/{id}/publish endpoint for manual publishing
- [x] 10.11 Create PATCH /grades/{id} endpoint for professor to edit LLM feedback/score
- [x] 10.12 Implement best score tracking across multiple submissions
- [x] 10.13 Handle LLM API failures (timeout, rate limit) with fallback to tests-only

## 11. Backend - Grades and Analytics

- [x] 11.1 Create GET /grades endpoint for professors (filter by class, exercise)
- [x] 11.2 Create GET /grades/me endpoint for students (own grades only)
- [x] 11.3 Implement CSV export of class grades
- [x] 11.4 Create GET /classes/{id}/progress endpoint showing completion stats per student

## 12. Frontend - Setup and Routing

- [ ] 12.1 Setup React Router with routes (login, register, dashboard)
- [ ] 12.2 Setup Axios for API calls with auth interceptors
- [ ] 12.3 Implement JWT storage in localStorage with refresh logic
- [ ] 12.4 Create protected route component checking authentication
- [ ] 12.5 Setup global state management (Context API or Zustand)

## 13. Frontend - Authentication UI

- [ ] 13.1 Create Login page with email/password form
- [ ] 13.2 Create Register page with validation (email, password >= 8 chars)
- [ ] 13.3 Create Password Reset Request page
- [ ] 13.4 Create Password Reset Confirm page (token from email link)
- [ ] 13.5 Implement form validation and error display
- [ ] 13.6 Add rate limiting feedback on login failures

## 14. Frontend - Professor Dashboard

- [ ] 14.1 Create Professor Dashboard layout with navigation
- [ ] 14.2 Create Classes List page showing professor's classes
- [ ] 14.3 Create Class Detail page with roster and groups
- [ ] 14.4 Create Create Class form
- [ ] 14.5 Create Invite Students form (manual email entry or CSV upload)
- [ ] 14.6 Display invite code for students to join
- [ ] 14.7 Create Exercise List page with create/edit buttons
- [ ] 14.8 Create Exercise Form (rich text editor for Markdown, file upload for datasets)
- [ ] 14.9 Implement Markdown preview with LaTeX rendering
- [ ] 14.10 Create Test Cases editor (add input/output, mark hidden)
- [ ] 14.11 Create Exercise List builder (drag-drop exercises, set weights)
- [ ] 14.12 Create Grades view (table with export CSV button)
- [ ] 14.13 Create Submission Review page (view code, tests, LLM feedback, edit score)
- [ ] 14.14 Implement batch grade publishing

## 15. Frontend - Student Dashboard

- [ ] 15.1 Create Student Dashboard layout with navigation
- [ ] 15.2 Create My Classes page listing enrolled classes
- [ ] 15.3 Create Join Class form (enter invite code)
- [ ] 15.4 Create Exercise Lists view (filter by class, show deadlines)
- [ ] 15.5 Create Exercise Detail page with description and starter code
- [ ] 15.6 Implement in-browser code editor with syntax highlighting (Monaco or CodeMirror)
- [ ] 15.7 Create file upload option for code submission
- [ ] 15.8 Display submission limit and remaining attempts
- [ ] 15.9 Create Submission History view with diff between attempts
- [ ] 15.10 Create Submission Results page (test results, LLM feedback, score)
- [ ] 15.11 Implement real-time status polling for running submissions
- [ ] 15.12 Create My Grades page showing scores per exercise and list

## 16. Testing and Documentation

- [ ] 16.1 Write unit tests for authentication endpoints
- [ ] 16.2 Write unit tests for class management endpoints
- [ ] 16.3 Write unit tests for exercise and submission endpoints
- [ ] 16.4 Write integration tests for sandbox execution
- [ ] 16.5 Write tests for grading logic (test score, LLM, composite)
- [ ] 16.6 Create API documentation (Swagger/OpenAPI via FastAPI)
- [ ] 16.7 Write README with setup instructions
- [ ] 16.8 Document environment variables and configuration

## 17. Deployment Preparation

- [ ] 17.1 Create production Dockerfile for backend
- [ ] 17.2 Create production Dockerfile for Celery worker
- [ ] 17.3 Setup environment-specific configs (dev, staging, prod)
- [ ] 17.4 Configure CORS for frontend domain
- [ ] 17.5 Setup HTTPS/SSL certificates
- [ ] 17.6 Configure database backups
- [ ] 17.7 Setup monitoring (Prometheus/Grafana or managed service)
- [ ] 17.8 Setup logging (structured logs with request IDs)
- [ ] 17.9 Configure alerting for queue depth and execution failures
- [ ] 17.10 Build and deploy frontend (Vercel/Netlify)
