from pathlib import Path

from django.conf import settings

from .utils import (
    api_response,
    auth_user,
    execute,
    fetch_all,
    fetch_one,
    hash_password,
    make_token,
    method_not_allowed,
    read_data,
    require_admin,
    save_upload,
    verify_password,
)


def health(_request):
    from datetime import datetime

    return api_response(
        {
            "success": True,
            "message": "CoWorkConnect API is healthy",
            "timestamp": datetime.utcnow().isoformat(),
        }
    )


def auth_test(_request):
    return api_response({"message": "Auth routes are working! Use POST for register/login."})


def register(request):
    if request.method != "POST":
        return method_not_allowed()

    data = read_data(request)
    name = data.get("name")
    email = (data.get("email") or "").strip().lower()
    password = data.get("password")
    role = data.get("role") or "user"

    if not name or not email or not password:
        return api_response({"success": False, "message": "Name, email and password are required"}, 400)

    if fetch_one("SELECT id FROM users WHERE LOWER(email) = LOWER(%s)", [email]):
        return api_response({"success": False, "message": "User already exists"}, 400)

    _, user_id = execute(
        "INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)",
        [name, email, hash_password(password), role],
    )
    return api_response({"success": True, "message": "User registered successfully", "userId": user_id}, 201)


def login(request):
    if request.method != "POST":
        return method_not_allowed()

    data = read_data(request)
    email = (data.get("email") or "").strip().lower()
    user = fetch_one("SELECT * FROM users WHERE LOWER(email) = LOWER(%s)", [email])
    if not user or not verify_password(data.get("password"), user["password"]):
        return api_response({"success": False, "message": "Invalid credentials"}, 401)

    return api_response(
        {
            "success": True,
            "token": make_token(user),
            "user": {"id": user["id"], "name": user["name"], "email": user["email"], "role": user["role"]},
        }
    )


def spaces(request):
    if request.method == "GET":
        sql = "SELECT * FROM spaces WHERE is_available = TRUE"
        params = []
        location = request.GET.get("location")
        space_type = request.GET.get("type")
        min_price = request.GET.get("minPrice")
        max_price = request.GET.get("maxPrice")

        if location:
            sql += " AND location LIKE %s"
            params.append(f"%{location}%")
        if space_type and space_type != "all":
            sql += " AND type = %s"
            params.append(space_type)
        if min_price:
            sql += " AND price_per_day >= %s"
            params.append(min_price)
        if max_price:
            sql += " AND price_per_day <= %s"
            params.append(max_price)

        rows = fetch_all(sql, params)
        return api_response({"success": True, "count": len(rows), "data": rows})

    if request.method == "POST":
        user, error = auth_user(request)
        if error:
            return error
        admin_error = require_admin(user)
        if admin_error:
            return admin_error

        data = read_data(request)
        _, space_id = execute(
            """
            INSERT INTO spaces (name, type, location, price_per_day, capacity, description, image_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            [
                data.get("name"),
                data.get("type"),
                data.get("location") or "General",
                data.get("price_per_day"),
                data.get("capacity"),
                data.get("description"),
                data.get("image_url"),
            ],
        )
        return api_response(
            {
                "success": True,
                "message": "Space created successfully",
                "data": {
                    "id": space_id,
                    "name": data.get("name"),
                    "type": data.get("type"),
                    "price_per_day": data.get("price_per_day"),
                    "capacity": data.get("capacity"),
                },
            },
            201,
        )

    return method_not_allowed()


def space_detail(request, space_id):
    if request.method == "GET":
        space = fetch_one("SELECT * FROM spaces WHERE id = %s", [space_id])
        if not space:
            return api_response({"success": False, "message": "Space not found"}, 404)
        return api_response({"success": True, "data": space})

    user, error = auth_user(request)
    if error:
        return error
    admin_error = require_admin(user)
    if admin_error:
        return admin_error

    if request.method == "PUT":
        data = read_data(request)
        fields = ["name", "type", "location", "price_per_day", "capacity", "description", "image_url", "is_available"]
        updates = [field for field in fields if field in data]
        if not updates:
            return api_response({"success": False, "message": "No fields to update"}, 400)
        sql = "UPDATE spaces SET " + ", ".join(f"{field} = %s" for field in updates) + " WHERE id = %s"
        rowcount, _ = execute(sql, [data[field] for field in updates] + [space_id])
        if rowcount == 0:
            return api_response({"success": False, "message": "Space not found"}, 404)
        return api_response({"success": True, "message": "Space updated successfully"})

    if request.method == "DELETE":
        rowcount, _ = execute("DELETE FROM spaces WHERE id = %s", [space_id])
        if rowcount == 0:
            return api_response({"success": False, "message": "Space not found"}, 404)
        return api_response({"success": True, "message": "Space deleted successfully"})

    return method_not_allowed()


def bookings(request):
    user, error = auth_user(request)
    if error:
        return error

    if request.method == "POST":
        data = read_data(request)
        space_id = data.get("spaceId")
        booking_date = data.get("bookingDate")
        space = fetch_one("SELECT * FROM spaces WHERE id = %s", [space_id])
        if not space:
            return api_response({"success": False, "message": "Space not found"}, 404)
        if not space["is_available"]:
            return api_response({"success": False, "message": "Space is currently not available"}, 400)
        existing = fetch_one(
            'SELECT id FROM bookings WHERE space_id = %s AND booking_date = %s AND status != "cancelled"',
            [space_id, booking_date],
        )
        if existing:
            return api_response({"success": False, "message": "Space is already booked for this date"}, 400)

        _, booking_id = execute(
            "INSERT INTO bookings (user_id, space_id, booking_date) VALUES (%s, %s, %s)",
            [user["id"], space_id, booking_date],
        )
        return api_response({"success": True, "message": "Booking request sent successfully", "bookingId": booking_id}, 201)

    if request.method == "GET":
        admin_error = require_admin(user)
        if admin_error:
            return admin_error
        rows = fetch_all(
            """
            SELECT b.*, u.name as user_name, u.email as user_email, s.name as space_name
            FROM bookings b
            JOIN users u ON b.user_id = u.id
            JOIN spaces s ON b.space_id = s.id
            """
        )
        return api_response({"success": True, "count": len(rows), "data": rows})

    return method_not_allowed()


def my_bookings(request):
    if request.method != "GET":
        return method_not_allowed()
    user, error = auth_user(request)
    if error:
        return error
    rows = fetch_all(
        """
        SELECT b.*, s.name as space_name, s.type as space_type
        FROM bookings b
        JOIN spaces s ON b.space_id = s.id
        WHERE b.user_id = %s
        """,
        [user["id"]],
    )
    return api_response({"success": True, "count": len(rows), "data": rows})


def booking_detail(request, booking_id):
    user, error = auth_user(request)
    if error:
        return error

    if request.method == "PUT":
        admin_error = require_admin(user)
        if admin_error:
            return admin_error
        status = read_data(request).get("status")
        rowcount, _ = execute("UPDATE bookings SET status = %s WHERE id = %s", [status, booking_id])
        if rowcount == 0:
            return api_response({"success": False, "message": "Booking not found"}, 404)
        return api_response({"success": True, "message": f"Booking status updated to {status}"})

    if request.method == "DELETE":
        booking = fetch_one("SELECT * FROM bookings WHERE id = %s", [booking_id])
        if not booking:
            return api_response({"success": False, "message": "Booking not found"}, 404)
        if booking["user_id"] != user["id"] and user.get("role") != "admin":
            return api_response({"success": False, "message": "Not authorized to cancel this booking"}, 403)
        execute('UPDATE bookings SET status = "cancelled" WHERE id = %s', [booking_id])
        return api_response({"success": True, "message": "Booking cancelled successfully"})

    return method_not_allowed()


def profile(request):
    user, error = auth_user(request)
    if error:
        return error

    if request.method == "GET":
        row = fetch_one("SELECT id, name, email, role, status, bio, created_at FROM users WHERE id = %s", [user["id"]])
        if not row:
            return api_response({"success": False, "message": "User not found"}, 404)
        return api_response({"success": True, "data": row})

    if request.method == "PUT":
        data = read_data(request)
        email = data.get("email")
        if email and fetch_one("SELECT id FROM users WHERE email = %s AND id != %s", [email, user["id"]]):
            return api_response({"success": False, "message": "Email already in use"}, 400)
        execute(
            """
            UPDATE users
            SET name = COALESCE(%s, name), email = COALESCE(%s, email), status = COALESCE(%s, status), bio = COALESCE(%s, bio)
            WHERE id = %s
            """,
            [data.get("name"), email, data.get("status"), data.get("bio"), user["id"]],
        )
        return api_response({"success": True, "message": "Profile updated successfully"})

    return method_not_allowed()


def update_password(request):
    if request.method != "PUT":
        return method_not_allowed()
    user, error = auth_user(request)
    if error:
        return error
    data = read_data(request)
    row = fetch_one("SELECT password FROM users WHERE id = %s", [user["id"]])
    if not row or not verify_password(data.get("currentPassword"), row["password"]):
        return api_response({"success": False, "message": "Current password is incorrect"}, 401)
    execute("UPDATE users SET password = %s WHERE id = %s", [hash_password(data.get("newPassword")), user["id"]])
    return api_response({"success": True, "message": "Password updated successfully"})


def search_users(request):
    query = request.GET.get("query")
    if not query:
        return api_response({"success": True, "data": []})
    rows = fetch_all(
        "SELECT id, name, status, bio FROM users WHERE name LIKE %s OR bio LIKE %s LIMIT 10",
        [f"%{query}%", f"%{query}%"],
    )
    return api_response({"success": True, "data": rows})


def posts(request):
    if request.method == "GET":
        current_user, _ = auth_user(request, required=False)
        tag = request.GET.get("tag")
        params = []
        sql = """
            SELECT p.*, u.name as user_name,
              (SELECT COUNT(*) FROM post_likes WHERE post_id = p.id) as likes_count,
              (SELECT COUNT(*) FROM comments WHERE post_id = p.id) as comments_count
            FROM posts p
            JOIN users u ON p.user_id = u.id
        """
        if tag:
            sql += " WHERE p.tags LIKE %s"
            params.append(f"%{tag}%")
        sql += " ORDER BY p.created_at DESC LIMIT 50"

        rows = fetch_all(sql, params)
        for post in rows:
            post["liked_by_me"] = False
            if current_user:
                post["liked_by_me"] = bool(
                    fetch_one("SELECT id FROM post_likes WHERE post_id = %s AND user_id = %s", [post["id"], current_user["id"]])
                )
            post["comments"] = fetch_all(
                """
                SELECT c.*, u.name as user_name
                FROM comments c
                JOIN users u ON c.user_id = u.id
                WHERE c.post_id = %s ORDER BY c.created_at ASC
                """,
                [post["id"]],
            )
        return api_response({"success": True, "count": len(rows), "data": rows})

    if request.method == "POST":
        user, error = auth_user(request)
        if error:
            return error
        image_url = save_upload(request.FILES["image"], "posts") if "image" in request.FILES else None
        data = read_data(request)
        _, post_id = execute(
            "INSERT INTO posts (user_id, content, tags, image_url) VALUES (%s, %s, %s, %s)",
            [user["id"], data.get("content"), data.get("tags") or None, image_url],
        )
        return api_response(
            {
                "success": True,
                "message": "Post shared",
                "data": {"id": post_id, "content": data.get("content"), "tags": data.get("tags"), "image_url": image_url},
            },
            201,
        )

    return method_not_allowed()


def toggle_like(request, post_id):
    if request.method != "POST":
        return method_not_allowed()
    user, error = auth_user(request)
    if error:
        return error
    existing = fetch_one("SELECT id FROM post_likes WHERE post_id = %s AND user_id = %s", [post_id, user["id"]])
    if existing:
        execute("DELETE FROM post_likes WHERE post_id = %s AND user_id = %s", [post_id, user["id"]])
        return api_response({"success": True, "liked": False})
    execute("INSERT INTO post_likes (post_id, user_id) VALUES (%s, %s)", [post_id, user["id"]])
    return api_response({"success": True, "liked": True})


def add_comment(request, post_id):
    if request.method != "POST":
        return method_not_allowed()
    user, error = auth_user(request)
    if error:
        return error
    content = read_data(request).get("content")
    _, comment_id = execute(
        "INSERT INTO comments (post_id, user_id, content) VALUES (%s, %s, %s)",
        [post_id, user["id"], content],
    )
    row = fetch_one("SELECT name FROM users WHERE id = %s", [user["id"]])
    return api_response({"success": True, "data": {"id": comment_id, "content": content, "user_name": row["name"]}}, 201)


def delete_post(request, post_id):
    if request.method != "DELETE":
        return method_not_allowed()
    user, error = auth_user(request)
    if error:
        return error
    post = fetch_one("SELECT * FROM posts WHERE id = %s", [post_id])
    if not post:
        return api_response({"success": False, "message": "Post not found"}, 404)
    if post["user_id"] != user["id"] and user.get("role") != "admin":
        return api_response({"success": False, "message": "Not authorized"}, 403)
    if post.get("image_url"):
        image_path = Path(settings.BASE_DIR) / post["image_url"].lstrip("/")
        if image_path.exists():
            image_path.unlink()
    execute("DELETE FROM posts WHERE id = %s", [post_id])
    return api_response({"success": True, "message": "Post removed"})


def groups(request):
    if request.method == "GET":
        rows = fetch_all(
            """
            SELECT g.*, u.name as creator_name,
              (SELECT COUNT(*) FROM group_members WHERE group_id = g.id) as member_count
            FROM community_groups g
            JOIN users u ON g.created_by = u.id
            """
        )
        return api_response({"success": True, "count": len(rows), "data": rows})

    if request.method == "POST":
        user, error = auth_user(request)
        if error:
            return error
        data = read_data(request)
        _, group_id = execute(
            "INSERT INTO community_groups (name, description, created_by) VALUES (%s, %s, %s)",
            [data.get("name"), data.get("description"), user["id"]],
        )
        execute("INSERT INTO group_members (group_id, user_id) VALUES (%s, %s)", [group_id, user["id"]])
        return api_response({"success": True, "data": {"id": group_id, "name": data.get("name"), "description": data.get("description")}}, 201)

    return method_not_allowed()


def join_group(request, group_id):
    if request.method != "POST":
        return method_not_allowed()
    user, error = auth_user(request)
    if error:
        return error
    if fetch_one("SELECT id FROM group_members WHERE group_id = %s AND user_id = %s", [group_id, user["id"]]):
        return api_response({"success": False, "message": "Already a member"}, 400)
    execute("INSERT INTO group_members (group_id, user_id) VALUES (%s, %s)", [group_id, user["id"]])
    return api_response({"success": True, "message": "Joined group successfully"})


def group_messages(request, group_id):
    user, error = auth_user(request)
    if error:
        return error

    if request.method == "GET":
        rows = fetch_all(
            """
            SELECT m.*, u.name as user_name
            FROM messages m
            JOIN users u ON m.user_id = u.id
            WHERE m.group_id = %s
            ORDER BY m.created_at ASC
            """,
            [group_id],
        )
        return api_response({"success": True, "data": rows})

    if request.method == "POST":
        content = read_data(request).get("content")
        _, message_id = execute(
            "INSERT INTO messages (group_id, user_id, content) VALUES (%s, %s, %s)",
            [group_id, user["id"], content],
        )
        row = fetch_one(
            """
            SELECT m.*, u.name as user_name
            FROM messages m
            JOIN users u ON m.user_id = u.id
            WHERE m.id = %s
            """,
            [message_id],
        )
        return api_response({"success": True, "message": "Message sent", "data": row}, 201)

    return method_not_allowed()


def events(request):
    if request.method == "GET":
        rows = fetch_all(
            """
            SELECT e.*, s.name as space_name, u.name as creator_name,
              (SELECT COUNT(*) FROM event_registrations WHERE event_id = e.id) as participant_count
            FROM events e
            LEFT JOIN spaces s ON e.space_id = s.id
            JOIN users u ON e.created_by = u.id
            ORDER BY e.event_date ASC
            """
        )
        return api_response({"success": True, "count": len(rows), "data": rows})

    if request.method == "POST":
        user, error = auth_user(request)
        if error:
            return error
        data = read_data(request)
        image_url = save_upload(request.FILES["image"]) if "image" in request.FILES else None
        space_id = data.get("spaceId") or None
        _, event_id = execute(
            """
            INSERT INTO events (title, city, venue, event_type, description, event_date, end_date, image_url, space_id, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            [
                data.get("title"),
                data.get("city") or None,
                data.get("venue") or None,
                data.get("eventType") or None,
                data.get("description"),
                data.get("eventDate"),
                data.get("endDate") or None,
                image_url,
                space_id,
                user["id"],
            ],
        )
        return api_response({"success": True, "data": {"id": event_id, "title": data.get("title"), "eventDate": data.get("eventDate")}}, 201)

    return method_not_allowed()


def register_event(request, event_id):
    if request.method != "POST":
        return method_not_allowed()
    user, error = auth_user(request)
    if error:
        return error
    if fetch_one("SELECT id FROM event_registrations WHERE event_id = %s AND user_id = %s", [event_id, user["id"]]):
        return api_response({"success": False, "message": "Already registered for this event"}, 400)
    execute("INSERT INTO event_registrations (event_id, user_id) VALUES (%s, %s)", [event_id, user["id"]])
    return api_response({"success": True, "message": "Successfully registered for event"})


def event_participants(request, event_id):
    if request.method != "GET":
        return method_not_allowed()
    user, error = auth_user(request)
    if error:
        return error
    rows = fetch_all(
        """
        SELECT u.id, u.name, u.email, r.registered_at
        FROM event_registrations r
        JOIN users u ON r.user_id = u.id
        WHERE r.event_id = %s
        """,
        [event_id],
    )
    return api_response({"success": True, "count": len(rows), "data": rows})
