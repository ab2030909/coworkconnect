# CoWorkConnect Django API

CoWorkConnect now runs on Django instead of Node/Express.

## Setup

```powershell
python -m pip install -r requirements.txt
python manage.py runserver 5000
```

The app reads `.env` automatically during local development:

```text
DEBUG=true
DJANGO_SECRET_KEY=use_a_long_random_secret_here
DATABASE_URL=postgresql://USER:PASSWORD@HOST:6543/postgres?sslmode=require
DB_SSL=true

# Optional local MySQL fallback:
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=...
DB_NAME=coworkconnect
DB_SSL=false
JWT_SECRET=use_a_long_random_secret_here
JWT_EXPIRE=30d
```

Django creates the MySQL database and required tables on startup if they do not exist.

## Optional Seed Data

Register at least one user, then run:

```powershell
python manage.py seed
```

## Endpoints

Base URL: `http://localhost:5000`

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| GET | `/api/health` | Health check |
| POST | `/api/auth/register` | Register user |
| POST | `/api/auth/login` | Login and receive JWT |
| GET | `/api/spaces` | List available spaces |
| GET | `/api/spaces/:id` | Get one space |
| POST | `/api/spaces` | Create space, admin only |
| PUT | `/api/spaces/:id` | Update space, admin only |
| DELETE | `/api/spaces/:id` | Delete space, admin only |
| POST | `/api/bookings` | Create booking |
| GET | `/api/bookings/my` | Current user's bookings |
| GET | `/api/bookings` | All bookings, admin only |
| PUT | `/api/bookings/:id` | Update booking status, admin only |
| DELETE | `/api/bookings/:id` | Cancel booking |
| GET | `/api/users/profile` | Current profile |
| PUT | `/api/users/profile` | Update profile |
| PUT | `/api/users/updatepassword` | Change password |
| GET | `/api/users/search?query=...` | Search user profiles |
| GET | `/api/posts` | Community feed |
| POST | `/api/posts` | Create post with optional `image` upload |
| POST | `/api/posts/:id/like` | Toggle post like |
| POST | `/api/posts/:id/comments` | Add comment |
| DELETE | `/api/posts/:id` | Delete own post or admin post |
| GET | `/api/groups` | List groups |
| POST | `/api/groups` | Create group |
| POST | `/api/groups/:id/join` | Join group |
| GET | `/api/groups/:id/messages` | Group messages |
| POST | `/api/groups/:id/messages` | Send group message |
| GET | `/api/events` | List events |
| POST | `/api/events` | Create event with optional `image` upload |
| POST | `/api/events/:id/register` | Register for event |
| GET | `/api/events/:id/participants` | Event participants |

Private routes require:

```text
Authorization: Bearer <token>
```
