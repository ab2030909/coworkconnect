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

VALID_SPACE_TYPES = {"desk", "private_office", "meeting_room", "virtual_office"}
VALID_BOOKING_STATUSES = {"pending", "confirmed", "cancelled"}


def require_fields(data, fields):
    missing = [field for field in fields if not data.get(field)]
    if missing:
        return api_response({"success": False, "message": f"Missing required fields: {', '.join(missing)}"}, 400)
    return None


def parse_positive_number(value, label):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None, api_response({"success": False, "message": f"{label} must be a valid number"}, 400)
    if number <= 0:
        return None, api_response({"success": False, "message": f"{label} must be greater than zero"}, 400)
    return number, None


def health(_request):
    from datetime import datetime
    from django.db import connection

    return api_response(
        {
            "success": True,
            "message": "CoWorkConnect API is healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "database": {
                "vendor": connection.vendor,
                "external_configured": settings.HAS_EXTERNAL_DB_CONFIG,
                "temporary_sqlite": settings.USE_SQLITE_FALLBACK,
            },
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
    role = "user"

    if not name or not email or not password:
        return api_response({"success": False, "message": "Name, email and password are required"}, 400)
    if len(password) < 8:
        return api_response({"success": False, "message": "Password must be at least 8 characters"}, 400)

    if fetch_one("SELECT id FROM users WHERE LOWER(email) = LOWER(%s)", [email]):
        return api_response({"success": False, "message": "User already exists"}, 400)

    _, user_id = execute(
        "INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)",
        [name, email, hash_password(password), role],
    )
    user = {"id": user_id, "name": name, "email": email, "role": role}
    return api_response(
        {
            "success": True,
            "message": "User registered successfully",
            "userId": user_id,
            "token": make_token(user),
            "user": user,
        },
        201,
    )


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
        missing = require_fields(data, ["name", "type", "price_per_day", "capacity"])
        if missing:
            return missing
        if data.get("type") not in VALID_SPACE_TYPES:
            return api_response({"success": False, "message": "Invalid workspace type"}, 400)
        price, error = parse_positive_number(data.get("price_per_day"), "Price")
        if error:
            return error
        capacity, error = parse_positive_number(data.get("capacity"), "Capacity")
        if error:
            return error
        _, space_id = execute(
            """
            INSERT INTO spaces (name, type, location, price_per_day, capacity, description, image_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            [
                data.get("name"),
                data.get("type"),
                data.get("location") or "General",
                price,
                int(capacity),
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
        if "type" in data and data.get("type") not in VALID_SPACE_TYPES:
            return api_response({"success": False, "message": "Invalid workspace type"}, 400)
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
        if not space_id or not booking_date:
            return api_response({"success": False, "message": "Space and booking date are required"}, 400)
        space = fetch_one("SELECT * FROM spaces WHERE id = %s", [space_id])
        if not space:
            return api_response({"success": False, "message": "Space not found"}, 404)
        if not space["is_available"]:
            return api_response({"success": False, "message": "Space is currently not available"}, 400)
        existing = fetch_one(
            "SELECT id FROM bookings WHERE space_id = %s AND booking_date = %s AND status != %s",
            [space_id, booking_date, "cancelled"],
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
        if status not in VALID_BOOKING_STATUSES:
            return api_response({"success": False, "message": "Invalid booking status"}, 400)
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
        execute("UPDATE bookings SET status = %s WHERE id = %s", ["cancelled", booking_id])
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
        email = (data.get("email") or "").strip().lower() or None
        if email and fetch_one("SELECT id FROM users WHERE LOWER(email) = LOWER(%s) AND id != %s", [email, user["id"]]):
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
    new_password = data.get("newPassword")
    if not new_password or len(new_password) < 8:
        return api_response({"success": False, "message": "New password must be at least 8 characters"}, 400)
    row = fetch_one("SELECT password FROM users WHERE id = %s", [user["id"]])
    if not row or not verify_password(data.get("currentPassword"), row["password"]):
        return api_response({"success": False, "message": "Current password is incorrect"}, 401)
    execute("UPDATE users SET password = %s WHERE id = %s", [hash_password(new_password), user["id"]])
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
        data = read_data(request)
        content = (data.get("content") or "").strip()
        if not content:
            return api_response({"success": False, "message": "Post content is required"}, 400)
        try:
            image_url = save_upload(request.FILES["image"], "posts") if "image" in request.FILES else None
        except ValueError as exc:
            return api_response({"success": False, "message": str(exc)}, 400)
        _, post_id = execute(
            "INSERT INTO posts (user_id, content, tags, image_url) VALUES (%s, %s, %s, %s)",
            [user["id"], content, data.get("tags") or None, image_url],
        )
        return api_response(
            {
                "success": True,
                "message": "Post shared",
                "data": {"id": post_id, "content": content, "tags": data.get("tags"), "image_url": image_url},
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
    if not existing and not fetch_one("SELECT id FROM posts WHERE id = %s", [post_id]):
        return api_response({"success": False, "message": "Post not found"}, 404)
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
    content = (read_data(request).get("content") or "").strip()
    if not content:
        return api_response({"success": False, "message": "Comment content is required"}, 400)
    if not fetch_one("SELECT id FROM posts WHERE id = %s", [post_id]):
        return api_response({"success": False, "message": "Post not found"}, 404)
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
        current_user, _ = auth_user(request, required=False)
        rows = fetch_all(
            """
            SELECT g.*, u.name as creator_name,
              (SELECT COUNT(*) FROM group_members WHERE group_id = g.id) as member_count
            FROM community_groups g
            JOIN users u ON g.created_by = u.id
            ORDER BY g.created_at DESC
            """
        )
        if current_user:
            for group in rows:
                group["joined_by_me"] = bool(
                    fetch_one(
                        "SELECT id FROM group_members WHERE group_id = %s AND user_id = %s",
                        [group["id"], current_user["id"]],
                    )
                )
                group["created_by_me"] = group.get("created_by") == current_user["id"]
        return api_response({"success": True, "count": len(rows), "data": rows})

    if request.method == "POST":
        user, error = auth_user(request)
        if error:
            return error
        data = read_data(request)
        if not (data.get("name") or "").strip():
            return api_response({"success": False, "message": "Group name is required"}, 400)
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
    if not fetch_one("SELECT id FROM community_groups WHERE id = %s", [group_id]):
        return api_response({"success": False, "message": "Group not found"}, 404)
    if fetch_one("SELECT id FROM group_members WHERE group_id = %s AND user_id = %s", [group_id, user["id"]]):
        return api_response({"success": False, "message": "Already a member"}, 400)
    execute("INSERT INTO group_members (group_id, user_id) VALUES (%s, %s)", [group_id, user["id"]])
    return api_response({"success": True, "message": "Joined group successfully"})


def group_messages(request, group_id):
    user, error = auth_user(request)
    if error:
        return error

    if request.method == "GET":
        if not fetch_one("SELECT id FROM community_groups WHERE id = %s", [group_id]):
            return api_response({"success": False, "message": "Group not found"}, 404)
        if user.get("role") != "admin" and not fetch_one("SELECT id FROM group_members WHERE group_id = %s AND user_id = %s", [group_id, user["id"]]):
            return api_response({"success": False, "message": "Join the group to view messages"}, 403)
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
        if not fetch_one("SELECT id FROM community_groups WHERE id = %s", [group_id]):
            return api_response({"success": False, "message": "Group not found"}, 404)
        if not fetch_one("SELECT id FROM group_members WHERE group_id = %s AND user_id = %s", [group_id, user["id"]]):
            execute("INSERT INTO group_members (group_id, user_id) VALUES (%s, %s)", [group_id, user["id"]])
        content = (read_data(request).get("content") or "").strip()
        try:
            image_url = save_upload(request.FILES["image"], "messages") if "image" in request.FILES else None
        except ValueError as exc:
            return api_response({"success": False, "message": str(exc)}, 400)
        if not content and not image_url:
            return api_response({"success": False, "message": "Write a message or attach an image"}, 400)
        _, message_id = execute(
            "INSERT INTO messages (group_id, user_id, content, image_url) VALUES (%s, %s, %s, %s)",
            [group_id, user["id"], content, image_url],
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
        missing = require_fields(data, ["title", "description", "eventDate"])
        if missing:
            return missing
        try:
            image_url = save_upload(request.FILES["image"], "events") if "image" in request.FILES else None
        except ValueError as exc:
            return api_response({"success": False, "message": str(exc)}, 400)
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
    if not fetch_one("SELECT id FROM events WHERE id = %s", [event_id]):
        return api_response({"success": False, "message": "Event not found"}, 404)
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
    event = fetch_one("SELECT created_by FROM events WHERE id = %s", [event_id])
    if not event:
        return api_response({"success": False, "message": "Event not found"}, 404)
    if user.get("role") != "admin" and event["created_by"] != user["id"]:
        return api_response({"success": False, "message": "Only the event host or admin can view participants"}, 403)
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
