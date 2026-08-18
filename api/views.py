import json
import urllib.parse
import urllib.request
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


import re

EMAIL_REGEX = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
PHONE_REGEX = r"^\+?[0-9]{7,15}$"


def validate_email_format(email):
    return bool(email and re.match(EMAIL_REGEX, email.strip()))


def validate_phone_format(phone):
    if not phone:
        return False
    clean = re.sub(r"[\s\-()]", "", str(phone).strip())
    return bool(re.match(PHONE_REGEX, clean))


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
    if not validate_email_format(email):
        return api_response({"success": False, "message": "Please enter a valid email address format (e.g. user@example.com)"}, 400)
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
    if not validate_email_format(email):
        return api_response({"success": False, "message": "Please enter a valid email address format (e.g. user@example.com)"}, 400)
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
        sql = "SELECT * FROM spaces WHERE (is_available IS TRUE OR is_available IS NULL)"
        params = []
        location = (request.GET.get("location") or "").strip()
        space_type = (request.GET.get("type") or "").strip()
        min_price = (request.GET.get("minPrice") or "").strip()
        max_price = (request.GET.get("maxPrice") or "").strip()
        sort = (request.GET.get("sort") or "").strip()

        if location and location.lower() != "anywhere":
            sql += " AND location LIKE %s"
            params.append(f"%{location}%")
        if space_type and space_type != "all":
            sql += " AND type = %s"
            params.append(space_type)
        if min_price:
            try:
                if float(min_price) > 0:
                    sql += " AND price_per_day >= %s"
                    params.append(min_price)
            except Exception:
                pass
        if max_price:
            try:
                if float(max_price) > 0:
                    sql += " AND price_per_day <= %s"
                    params.append(max_price)
            except Exception:
                pass

        if sort == "price_asc":
            sql += " ORDER BY price_per_day ASC"
        elif sort == "price_desc":
            sql += " ORDER BY price_per_day DESC"
        elif sort == "latest":
            sql += " ORDER BY id DESC"
        elif sort == "name":
            sql += " ORDER BY name ASC"
        else:
            sql += " ORDER BY id DESC"

        rows = fetch_all(sql, params)
        for row in rows:
            raw_imgs = row.get("images")
            imgs_list = []
            if raw_imgs:
                try:
                    imgs_list = json.loads(raw_imgs) if raw_imgs.startswith("[") else [s.strip() for s in raw_imgs.split(",") if s.strip()]
                except Exception:
                    imgs_list = [raw_imgs]
            if not imgs_list and row.get("image_url"):
                imgs_list = [row["image_url"]]
            row["images_list"] = imgs_list[:5]

            raw_amenities = row.get("amenities")
            amenities_list = []
            if raw_amenities:
                try:
                    amenities_list = json.loads(raw_amenities) if raw_amenities.startswith("[") else [s.strip() for s in raw_amenities.split(",") if s.strip()]
                except Exception:
                    amenities_list = [raw_amenities]
            row["amenities_list"] = amenities_list

            raw_plans = row.get("pricing_plans")
            plans_list = []
            if raw_plans:
                try:
                    plans_list = json.loads(raw_plans) if isinstance(raw_plans, str) and raw_plans.startswith("[") else []
                except Exception:
                    plans_list = []
            row["pricing_plans_list"] = plans_list

        return api_response({"success": True, "count": len(rows), "data": rows})

    if request.method == "POST":
        user, error = auth_user(request)
        if error:
            return error

        data = read_data(request)
        missing = require_fields(data, ["name", "type", "price_per_day", "capacity", "contact_email", "contact_phone"])
        if missing:
            return missing
        if data.get("type") not in VALID_SPACE_TYPES:
            return api_response({"success": False, "message": "Invalid workspace type"}, 400)
        
        contact_email = (data.get("contact_email") or "").strip().lower()
        if not validate_email_format(contact_email):
            return api_response({"success": False, "message": "Please enter a valid contact email format (e.g. contact@workspace.com)"}, 400)

        contact_phone = (data.get("contact_phone") or "").strip()
        if not validate_phone_format(contact_phone):
            return api_response({"success": False, "message": "Please enter a valid numeric WhatsApp / Contact number (e.g. 03001234567 or +923001234567)"}, 400)

        price, error = parse_positive_number(data.get("price_per_day"), "Price")
        if error:
            return error
        capacity, error = parse_positive_number(data.get("capacity"), "Capacity")
        if error:
            return error

        images_input = data.get("images") or []
        if isinstance(images_input, list):
            images_str = json.dumps(images_input[:5])
            primary_image = images_input[0] if images_input else data.get("image_url")
        else:
            images_str = str(images_input)
            primary_image = data.get("image_url")

        amenities_input = data.get("amenities") or []
        amenities_str = json.dumps(amenities_input) if isinstance(amenities_input, list) else str(amenities_input)

        plans_input = data.get("pricing_plans") or []
        pricing_plans_str = None
        if isinstance(plans_input, list):
            valid_plans = []
            for p in plans_input:
                if isinstance(p, dict) and p.get("name") and (p.get("price") or p.get("price_per_day")):
                    valid_plans.append({
                        "name": str(p.get("name")).strip(),
                        "description": str(p.get("description") or "").strip(),
                        "price": str(p.get("price") or p.get("price_per_day")).strip(),
                        "period": str(p.get("period") or "per day").strip()
                    })
            if valid_plans:
                pricing_plans_str = json.dumps(valid_plans)

        rating_val = 5.0

        # Check and ensure pricing_plans column exists
        try:
            execute("ALTER TABLE spaces ADD COLUMN pricing_plans TEXT")
        except Exception:
            pass

        _, space_id = execute(
            """
            INSERT INTO spaces (name, type, location, price_per_day, capacity, description, image_url, images, rating, user_id, contact_email, contact_phone, website_url, amenities, pricing_plans, is_available)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            [
                data.get("name"),
                data.get("type"),
                data.get("location") or "General",
                price,
                int(capacity),
                data.get("description"),
                primary_image,
                images_str,
                rating_val,
                user["id"],
                contact_email,
                (data.get("contact_phone") or "").strip(),
                (data.get("website_url") or "").strip() or None,
                amenities_str,
                pricing_plans_str,
                True,
            ],
        )
        return api_response(
            {
                "success": True,
                "message": "Space created successfully",
                "data": {"id": space_id},
            },
            201,
        )

    return method_not_allowed()


def upload_file(request):
    user, error = auth_user(request)
    if error:
        return error

    if request.method == "POST":
        file_obj = request.FILES.get("file") or request.FILES.get("avatar") or request.FILES.get("image")
        if not file_obj:
            return api_response({"success": False, "message": "No file uploaded"}, 400)
        try:
            url = save_upload(file_obj, "uploads")
            return api_response({"success": True, "url": url, "avatar_url": url, "message": "File uploaded successfully"})
        except Exception as e:
            return api_response({"success": False, "message": str(e)}, 400)

    return method_not_allowed()


def space_detail(request, space_id):
    if request.method == "GET":
        space = fetch_one("SELECT * FROM spaces WHERE id = %s", [space_id])
        if not space:
            return api_response({"success": False, "message": "Space not found"}, 404)
        
        raw_imgs = space.get("images")
        imgs_list = []
        if raw_imgs:
            try:
                imgs_list = json.loads(raw_imgs) if raw_imgs.startswith("[") else [s.strip() for s in raw_imgs.split(",") if s.strip()]
            except Exception:
                imgs_list = [raw_imgs]
        if not imgs_list and space.get("image_url"):
            imgs_list = [space["image_url"]]
        space["images_list"] = imgs_list[:5]

        raw_amenities = space.get("amenities")
        amenities_list = []
        if raw_amenities:
            try:
                amenities_list = json.loads(raw_amenities) if raw_amenities.startswith("[") else [s.strip() for s in raw_amenities.split(",") if s.strip()]
            except Exception:
                amenities_list = [raw_amenities]
        space["amenities_list"] = amenities_list

        raw_plans = space.get("pricing_plans")
        plans_list = []
        if raw_plans:
            try:
                plans_list = json.loads(raw_plans) if isinstance(raw_plans, str) and raw_plans.startswith("[") else []
            except Exception:
                plans_list = []
        space["pricing_plans_list"] = plans_list

        return api_response({"success": True, "data": space})

    user, error = auth_user(request)
    if error:
        return error

    space = fetch_one("SELECT * FROM spaces WHERE id = %s", [space_id])
    if not space:
        return api_response({"success": False, "message": "Space not found"}, 404)

    user_id_val = space.get("user_id")
    is_creator = (user_id_val is not None and int(user_id_val) == int(user["id"]))
    is_admin = user.get("role") == "admin"
    if user_id_val is None:
        is_creator = True

    if not is_creator and not is_admin:
        return api_response({"success": False, "message": "You are not authorized to modify or delete this workspace"}, 403)

    if request.method == "PUT":
        data = read_data(request)
        fields = ["name", "type", "location", "price_per_day", "capacity", "description", "image_url", "is_available"]
        updates = [field for field in fields if field in data]
        if not updates:
            return api_response({"success": False, "message": "No fields to update"}, 400)
        if "type" in data and data.get("type") not in VALID_SPACE_TYPES:
            return api_response({"success": False, "message": "Invalid workspace type"}, 400)
        sql = "UPDATE spaces SET " + ", ".join(f"{field} = %s" for field in updates) + " WHERE id = %s"
        execute(sql, [data[field] for field in updates] + [space_id])
        return api_response({"success": True, "message": "Space updated successfully"})

    if request.method == "DELETE":
        try:
            execute("DELETE FROM bookings WHERE space_id = %s", [space_id])
        except Exception:
            pass
        try:
            execute("UPDATE events SET space_id = NULL WHERE space_id = %s", [space_id])
        except Exception:
            pass
        execute("DELETE FROM spaces WHERE id = %s", [space_id])
        return api_response({"success": True, "message": "Workspace deleted successfully"})

    return method_not_allowed()


def location_suggestions(request):
    if request.method != "GET":
        return method_not_allowed()

    q = (request.GET.get("q") or "").strip()
    results = []
    seen = set()

    # Search strictly within registered workspaces in the database
    try:
        if q:
            db_rows = fetch_all(
                """
                SELECT location, COUNT(*) as space_count 
                FROM spaces 
                WHERE location IS NOT NULL AND location != '' AND LOWER(location) LIKE %s 
                GROUP BY location 
                ORDER BY space_count DESC, location ASC 
                LIMIT 12
                """,
                [f"%{q.lower()}%"],
            )
        else:
            db_rows = fetch_all(
                """
                SELECT location, COUNT(*) as space_count 
                FROM spaces 
                WHERE location IS NOT NULL AND location != '' 
                GROUP BY location 
                ORDER BY space_count DESC, location ASC 
                LIMIT 10
                """
            )
        for row in db_rows:
            loc = (row.get("location") or "").strip()
            count = row.get("space_count") or 1
            if loc and loc.lower() not in seen:
                seen.add(loc.lower())
                parts = [p.strip() for p in loc.split(",") if p.strip()]
                area = parts[0] if parts else loc
                city = parts[1] if len(parts) > 1 else ""
                badge_text = f"{count} Space" if count == 1 else f"{count} Spaces"
                results.append({
                    "full_name": loc,
                    "area": area,
                    "city": city or "Registered Space",
                    "type": "workspace",
                    "badge": badge_text,
                })
    except Exception:
        pass

    return api_response({"success": True, "count": len(results), "data": results})


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
        row = fetch_one(
            """
            SELECT id, name, email, role, status, bio, headline, avatar_url, expertise, github_url, linkedin_url, created_at,
              (SELECT COUNT(*) FROM friendships WHERE (user_id = users.id OR friend_id = users.id) AND status = 'accepted') as friends_count
            FROM users WHERE id = %s
            """,
            [user["id"]]
        )
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
            SET name = COALESCE(%s, name), 
                email = COALESCE(%s, email), 
                status = COALESCE(%s, status), 
                bio = COALESCE(%s, bio),
                headline = CASE WHEN %s IS NOT NULL THEN %s ELSE headline END,
                avatar_url = CASE WHEN %s IS NOT NULL THEN %s ELSE avatar_url END,
                expertise = CASE WHEN %s IS NOT NULL THEN %s ELSE expertise END,
                github_url = CASE WHEN %s IS NOT NULL THEN %s ELSE github_url END,
                linkedin_url = CASE WHEN %s IS NOT NULL THEN %s ELSE linkedin_url END
            WHERE id = %s
            """,
            [
                data.get("name"), email, data.get("status"), data.get("bio"),
                data.get("headline") if "headline" in data else None, data.get("headline") if "headline" in data else None,
                data.get("avatar_url") if "avatar_url" in data else None, data.get("avatar_url") if "avatar_url" in data else None,
                data.get("expertise") if "expertise" in data else None, data.get("expertise") if "expertise" in data else None,
                data.get("github_url") if "github_url" in data else (data.get("githubUrl") if "githubUrl" in data else None),
                data.get("github_url") if "github_url" in data else (data.get("githubUrl") if "githubUrl" in data else None),
                data.get("linkedin_url") if "linkedin_url" in data else (data.get("linkedinUrl") if "linkedinUrl" in data else None),
                data.get("linkedin_url") if "linkedin_url" in data else (data.get("linkedinUrl") if "linkedinUrl" in data else None),
                user["id"]
            ],
        )
        return api_response({"success": True, "message": "Profile updated successfully"})

    return method_not_allowed()


def public_profile(request, user_id):
    if request.method != "GET":
        return method_not_allowed()
    current_user, _ = auth_user(request, required=False)
    
    target_user = fetch_one(
        """
        SELECT id, name, email, role, status, bio, headline, avatar_url, expertise, github_url, linkedin_url, created_at,
          (SELECT COUNT(*) FROM friendships WHERE (user_id = users.id OR friend_id = users.id) AND status = 'accepted') as friends_count
        FROM users WHERE id = %s
        """,
        [user_id]
    )
    if not target_user:
        return api_response({"success": False, "message": "User not found"}, 404)

    friendship_status = "none"
    if current_user:
        if current_user["id"] == user_id:
            friendship_status = "self"
        else:
            rel = fetch_one(
                """
                SELECT id, user_id, friend_id, status FROM friendships
                WHERE (user_id = %s AND friend_id = %s) OR (user_id = %s AND friend_id = %s)
                """,
                [current_user["id"], user_id, user_id, current_user["id"]]
            )
            if rel:
                if rel["status"] == "accepted":
                    friendship_status = "friends"
                elif rel["user_id"] == current_user["id"]:
                    friendship_status = "pending_sent"
                else:
                    friendship_status = "pending_received"

    target_user["friendship_status"] = friendship_status
    return api_response({"success": True, "data": target_user})


def friends_list(request):
    user, error = auth_user(request)
    if error:
        return error
    if request.method != "GET":
        return method_not_allowed()

    friends = fetch_all(
        """
        SELECT u.id, u.name, u.email, u.status, u.avatar_url, u.bio, f.created_at as friendship_date
        FROM friendships f
        JOIN users u ON (CASE WHEN f.user_id = %s THEN f.friend_id ELSE f.user_id END) = u.id
        WHERE (f.user_id = %s OR f.friend_id = %s) AND f.status = 'accepted'
        ORDER BY f.created_at DESC
        """,
        [user["id"], user["id"], user["id"]]
    )

    pending_received = fetch_all(
        """
        SELECT f.id as request_id, u.id as user_id, u.name, u.email, u.avatar_url, f.created_at
        FROM friendships f
        JOIN users u ON f.user_id = u.id
        WHERE f.friend_id = %s AND f.status = 'pending'
        ORDER BY f.created_at DESC
        """,
        [user["id"]]
    )

    pending_sent = fetch_all(
        """
        SELECT f.id as request_id, u.id as user_id, u.name, u.email, u.avatar_url, f.created_at
        FROM friendships f
        JOIN users u ON f.friend_id = u.id
        WHERE f.user_id = %s AND f.status = 'pending'
        ORDER BY f.created_at DESC
        """,
        [user["id"]]
    )

    return api_response({
        "success": True,
        "friends": friends,
        "pending_received": pending_received,
        "pending_sent": pending_sent
    })


def user_friends(request, user_id):
    if request.method != "GET":
        return method_not_allowed()
    
    friends = fetch_all(
        """
        SELECT u.id, u.name, u.email, u.status, u.avatar_url, u.bio
        FROM friendships f
        JOIN users u ON (CASE WHEN f.user_id = %s THEN f.friend_id ELSE f.user_id END) = u.id
        WHERE (f.user_id = %s OR f.friend_id = %s) AND f.status = 'accepted'
        ORDER BY f.created_at DESC
        """,
        [user_id, user_id, user_id]
    )
    return api_response({"success": True, "count": len(friends), "data": friends})


def send_friend_request(request):
    if request.method != "POST":
        return method_not_allowed()
    user, error = auth_user(request)
    if error:
        return error
    data = read_data(request)
    friend_id = data.get("friend_id") or data.get("friendId")
    if not friend_id or int(friend_id) == user["id"]:
        return api_response({"success": False, "message": "Invalid friend ID"}, 400)

    existing = fetch_one(
        "SELECT * FROM friendships WHERE (user_id = %s AND friend_id = %s) OR (user_id = %s AND friend_id = %s)",
        [user["id"], friend_id, friend_id, user["id"]]
    )
    if existing:
        if existing["status"] == "accepted":
            return api_response({"success": True, "message": "Already friends", "status": "friends"})
        if existing["user_id"] == user["id"]:
            return api_response({"success": True, "message": "Friend request already sent", "status": "pending_sent"})
        else:
            execute("UPDATE friendships SET status = 'accepted' WHERE id = %s", [existing["id"]])
            return api_response({"success": True, "message": "Friend request accepted!", "status": "friends"})

    execute("INSERT INTO friendships (user_id, friend_id, status) VALUES (%s, %s, 'pending')", [user["id"], friend_id])
    return api_response({"success": True, "message": "Friend request sent!", "status": "pending_sent"})


def respond_friend_request(request):
    if request.method != "PUT":
        return method_not_allowed()
    user, error = auth_user(request)
    if error:
        return error
    data = read_data(request)
    friend_id = data.get("friend_id") or data.get("friendId")
    action = (data.get("action") or "").strip().lower()

    if not friend_id:
        return api_response({"success": False, "message": "Friend ID is required"}, 400)

    existing = fetch_one(
        "SELECT * FROM friendships WHERE (user_id = %s AND friend_id = %s) OR (user_id = %s AND friend_id = %s)",
        [user["id"], friend_id, friend_id, user["id"]]
    )
    if not existing:
        return api_response({"success": False, "message": "No relationship found"}, 404)

    if action == "accept":
        execute("UPDATE friendships SET status = 'accepted' WHERE id = %s", [existing["id"]])
        return api_response({"success": True, "message": "Friend request accepted!", "status": "friends"})
    elif action in ["decline", "unfriend", "cancel"]:
        execute("DELETE FROM friendships WHERE id = %s", [existing["id"]])
        return api_response({"success": True, "message": "Relationship removed", "status": "none"})

    return api_response({"success": False, "message": "Invalid action"}, 400)


def profile_avatar(request):
    user, error = auth_user(request)
    if error:
        return error

    if request.method == "POST":
        if "avatar" not in request.FILES:
            return api_response({"success": False, "message": "No avatar file provided"}, 400)
        try:
            avatar_url = save_upload(request.FILES["avatar"], "avatars")
            execute("UPDATE users SET avatar_url = %s WHERE id = %s", [avatar_url, user["id"]])
            return api_response({"success": True, "avatar_url": avatar_url, "message": "Avatar uploaded successfully"})
        except Exception as e:
            return api_response({"success": False, "message": str(e)}, 500)

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
    query = (request.GET.get("query") or "").strip()
    if query:
        rows = fetch_all(
            "SELECT id, name, status, bio, avatar_url, headline, role FROM users WHERE name LIKE %s OR bio LIKE %s OR headline LIKE %s LIMIT 10",
            [f"%{query}%", f"%{query}%", f"%{query}%"],
        )
    else:
        rows = fetch_all(
            "SELECT id, name, status, bio, avatar_url, headline, role FROM users ORDER BY id DESC LIMIT 8"
        )
    return api_response({"success": True, "data": rows})


def posts(request):
    if request.method == "GET":
        current_user, _ = auth_user(request, required=False)
        tag = request.GET.get("tag")
        filter_user_id = request.GET.get("user_id") or request.GET.get("userId")
        
        if current_user:
            sql = """
                SELECT p.*, COALESCE(u.name, 'Community Member') as user_name, u.avatar_url as user_avatar, u.status as user_status, u.headline as user_headline, u.bio as user_bio,
                  (SELECT COUNT(*) FROM post_likes WHERE post_id = p.id) as likes_count,
                  (SELECT COUNT(*) FROM comments WHERE post_id = p.id) as comments_count,
                  CASE WHEN pl.id IS NOT NULL THEN 1 ELSE 0 END as liked_by_me
                FROM posts p
                LEFT JOIN users u ON p.user_id = u.id
                LEFT JOIN post_likes pl ON pl.post_id = p.id AND pl.user_id = %s
            """
            params = [current_user["id"]]
        else:
            sql = """
                SELECT p.*, COALESCE(u.name, 'Community Member') as user_name, u.avatar_url as user_avatar, u.status as user_status, u.headline as user_headline, u.bio as user_bio,
                  (SELECT COUNT(*) FROM post_likes WHERE post_id = p.id) as likes_count,
                  (SELECT COUNT(*) FROM comments WHERE post_id = p.id) as comments_count,
                  0 as liked_by_me
                FROM posts p
                LEFT JOIN users u ON p.user_id = u.id
            """
            params = []

        conditions = []
        if tag:
            conditions.append("p.tags LIKE %s")
            params.append(f"%{tag}%")
        if filter_user_id:
            conditions.append("p.user_id = %s")
            params.append(filter_user_id)
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)

        sql += " ORDER BY p.created_at DESC LIMIT 50"

        rows = fetch_all(sql, params)
        if not rows and not tag and not filter_user_id:
            # Seed initial vibrant posts if database has no posts yet
            admin_user = fetch_one("SELECT id FROM users LIMIT 1")
            user_id_to_use = admin_user["id"] if admin_user else 1
            seed_posts = [
                ("Welcome to CoWorkConnect Network! Share your projects, workspace reviews, and collaboration opportunities with local professionals across Pakistan.", "#community #networking"),
                ("Looking for recommended coworking spots in Islamabad with high-speed internet and quiet meeting rooms for client calls. Any suggestions?", "#islamabad #remote"),
                ("Hosted our team design sprint at Hive Mind Hub today. Great ergonomic setups and coffee!", "#startup #coworking")
            ]
            for text, t_tags in seed_posts:
                try:
                    execute("INSERT INTO posts (user_id, content, tags) VALUES (%s, %s, %s)", [user_id_to_use, text, t_tags])
                except Exception:
                    pass
            rows = fetch_all(sql, params)

        if rows:
            post_ids = [p["id"] for p in rows]
            placeholders = ", ".join(["%s"] * len(post_ids))
            all_comments = fetch_all(
                f"""
                SELECT c.*, COALESCE(u.name, 'Community Member') as user_name, u.avatar_url as user_avatar,
                  (SELECT COUNT(*) FROM comment_likes WHERE comment_id = c.id) as likes_count
                FROM comments c
                LEFT JOIN users u ON c.user_id = u.id
                WHERE c.post_id IN ({placeholders}) ORDER BY c.created_at ASC
                """,
                post_ids,
            )
            
            user_liked_comment_ids = set()
            if current_user and all_comments:
                liked_rows = fetch_all(
                    f"SELECT comment_id FROM comment_likes WHERE user_id = %s AND comment_id IN ({', '.join(['%s'] * len(all_comments))})",
                    [current_user["id"]] + [c["id"] for c in all_comments],
                )
                user_liked_comment_ids = {r["comment_id"] for r in liked_rows}

            comments_by_post = {}
            for comment in all_comments:
                comment["liked_by_me"] = comment["id"] in user_liked_comment_ids
                comments_by_post.setdefault(comment["post_id"], []).append(comment)

            for post in rows:
                post["liked_by_me"] = bool(post.get("liked_by_me"))
                post["comments"] = comments_by_post.get(post["id"], [])
        return api_response({"success": True, "count": len(rows), "data": rows})

    if request.method == "POST":
        user, error = auth_user(request)
        if error:
            return error
        data = read_data(request)
        content = (data.get("content") or request.POST.get("content") or "").strip()
        tags_val = data.get("tags") or request.POST.get("tags") or None
        if not content:
            return api_response({"success": False, "message": "Post content is required"}, 400)
        try:
            image_url = save_upload(request.FILES["image"], "posts") if "image" in request.FILES else None
        except ValueError as exc:
            return api_response({"success": False, "message": str(exc)}, 400)
        _, post_id = execute(
            "INSERT INTO posts (user_id, content, tags, image_url) VALUES (%s, %s, %s, %s)",
            [user["id"], content, tags_val, image_url],
        )
        return api_response(
            {
                "success": True,
                "message": "Post shared",
                "data": {"id": post_id, "content": content, "tags": tags_val, "image_url": image_url},
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
    data = read_data(request)
    content = (data.get("content") or "").strip()
    parent_id = data.get("parentId")
    if not content:
        return api_response({"success": False, "message": "Comment content is required"}, 400)
    if not fetch_one("SELECT id FROM posts WHERE id = %s", [post_id]):
        return api_response({"success": False, "message": "Post not found"}, 404)
    if parent_id and not fetch_one("SELECT id FROM comments WHERE id = %s", [parent_id]):
        return api_response({"success": False, "message": "Parent comment not found"}, 404)
    _, comment_id = execute(
        "INSERT INTO comments (post_id, user_id, parent_id, content) VALUES (%s, %s, %s, %s)",
        [post_id, user["id"], parent_id, content],
    )
    row = fetch_one("SELECT name, avatar_url FROM users WHERE id = %s", [user["id"]])
    return api_response({
        "success": True,
        "data": {
            "id": comment_id,
            "parent_id": parent_id,
            "content": content,
            "user_id": user["id"],
            "user_name": row["name"] if row else "You",
            "user_avatar": row.get("avatar_url") if row else None,
            "created_at": "Just now",
            "likes_count": 0,
            "liked_by_me": False
        }
    }, 201)


def toggle_comment_like(request, comment_id):
    if request.method != "POST":
        return method_not_allowed()
    user, error = auth_user(request)
    if error:
        return error
    if not fetch_one("SELECT id FROM comments WHERE id = %s", [comment_id]):
        return api_response({"success": False, "message": "Comment not found"}, 404)
    
    existing = fetch_one("SELECT id FROM comment_likes WHERE comment_id = %s AND user_id = %s", [comment_id, user["id"]])
    if existing:
        execute("DELETE FROM comment_likes WHERE id = %s", [existing["id"]])
        liked = False
    else:
        execute("INSERT INTO comment_likes (comment_id, user_id) VALUES (%s, %s)", [comment_id, user["id"]])
        liked = True
    return api_response({"success": True, "liked": liked})


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
            SELECT g.*, u.name as creator_name, u.avatar_url as creator_avatar,
              (SELECT COUNT(*) FROM group_members WHERE group_id = g.id) as member_count
            FROM community_groups g
            LEFT JOIN users u ON g.created_by = u.id
            ORDER BY g.created_at DESC
            """
        )
        if current_user and rows:
            my_memberships = fetch_all(
                "SELECT group_id, role FROM group_members WHERE user_id = %s",
                [current_user["id"]]
            )
            membership_map = {m["group_id"]: m["role"] for m in my_memberships}
            for group in rows:
                group["joined_by_me"] = group["id"] in membership_map
                group["my_role"] = membership_map.get(group["id"])
                group["created_by_me"] = group.get("created_by") == current_user["id"]
        else:
            for group in rows:
                group["joined_by_me"] = False
                group["my_role"] = None
                group["created_by_me"] = False
        return api_response({"success": True, "count": len(rows), "data": rows})

    if request.method == "POST":
        user, error = auth_user(request)
        if error:
            return error
        data = read_data(request)
        name = (data.get("name") or "").strip()
        if not name:
            return api_response({"success": False, "message": "Group name is required"}, 400)
        
        image_url = data.get("image_url") or None
        if "image" in request.FILES:
            try:
                image_url = save_upload(request.FILES["image"], "groups")
            except Exception as e:
                return api_response({"success": False, "message": str(e)}, 400)

        description = data.get("description") or None
        
        _, group_id = execute(
            "INSERT INTO community_groups (name, description, image_url, created_by) VALUES (%s, %s, %s, %s)",
            [name, description, image_url, user["id"]],
        )
        execute("INSERT INTO group_members (group_id, user_id, role) VALUES (%s, %s, %s)", [group_id, user["id"], "admin"])
        return api_response({"success": True, "data": {"id": group_id, "name": name, "description": description, "image_url": image_url}}, 201)

    return method_not_allowed()


def group_detail(request, group_id):
    group = fetch_one("SELECT g.*, u.name as creator_name, u.avatar_url as creator_avatar FROM community_groups g LEFT JOIN users u ON g.created_by = u.id WHERE g.id = %s", [group_id])
    if not group:
        return api_response({"success": False, "message": "Group not found"}, 404)

    if request.method == "GET":
        current_user, _ = auth_user(request, required=False)
        if current_user:
            member_rec = fetch_one("SELECT role FROM group_members WHERE group_id = %s AND user_id = %s", [group_id, current_user["id"]])
            group["joined_by_me"] = bool(member_rec)
            group["my_role"] = member_rec.get("role") if member_rec else None
            group["is_admin"] = group["created_by"] == current_user["id"] or (member_rec and member_rec.get("role") in ["admin", "co-admin"])
        return api_response({"success": True, "data": group})

    if request.method == "PUT":
        user, error = auth_user(request)
        if error:
            return error
        
        member_rec = fetch_one("SELECT role FROM group_members WHERE group_id = %s AND user_id = %s", [group_id, user["id"]])
        is_authorized = group["created_by"] == user["id"] or (member_rec and member_rec.get("role") in ["admin", "co-admin"]) or user.get("role") == "admin"
        if not is_authorized:
            return api_response({"success": False, "message": "Only admins can update group details"}, 403)

        data = read_data(request)
        name = data.get("name") or group.get("name")
        description = data.get("description") if "description" in data else group.get("description")
        image_url = data.get("image_url") if "image_url" in data else group.get("image_url")

        if "image" in request.FILES:
            try:
                image_url = save_upload(request.FILES["image"], "groups")
            except Exception as e:
                return api_response({"success": False, "message": str(e)}, 400)
        elif "file" in request.FILES:
            try:
                image_url = save_upload(request.FILES["file"], "groups")
            except Exception as e:
                return api_response({"success": False, "message": str(e)}, 400)

        execute(
            "UPDATE community_groups SET name = %s, description = %s, image_url = %s WHERE id = %s",
            [name, description, image_url, group_id],
        )
        return api_response({"success": True, "message": "Group details updated successfully", "image_url": image_url})

    if request.method == "DELETE":
        user, error = auth_user(request)
        if error:
            return error

        member_rec = fetch_one("SELECT role FROM group_members WHERE group_id = %s AND user_id = %s", [group_id, user["id"]])
        is_authorized = group["created_by"] == user["id"] or (member_rec and member_rec.get("role") in ["admin", "co-admin"]) or user.get("role") == "admin"
        if not is_authorized:
            return api_response({"success": False, "message": "Only group admins can delete this group"}, 403)

        execute("DELETE FROM community_groups WHERE id = %s", [group_id])
        return api_response({"success": True, "message": "Group deleted successfully"})

    return method_not_allowed()


def group_members_list(request, group_id):
    if not fetch_one("SELECT id FROM community_groups WHERE id = %s", [group_id]):
        return api_response({"success": False, "message": "Group not found"}, 404)

    if request.method == "GET":
        rows = fetch_all(
            """
            SELECT gm.id, gm.group_id, gm.user_id, COALESCE(gm.role, 'member') as member_role, gm.joined_at,
                   u.name as user_name, u.email as user_email, u.avatar_url as user_avatar, u.status as user_status
            FROM group_members gm
            JOIN users u ON gm.user_id = u.id
            WHERE gm.group_id = %s
            ORDER BY (CASE WHEN gm.role = 'admin' THEN 1 WHEN gm.role = 'co-admin' THEN 2 ELSE 3 END), u.name ASC
            """,
            [group_id],
        )
        return api_response({"success": True, "data": rows})

    if request.method == "POST":
        user, error = auth_user(request)
        if error:
            return error
        
        data = read_data(request)
        target_id = data.get("user_id")
        target_email = (data.get("email") or "").strip().lower()

        if not target_id and target_email:
            found_u = fetch_one("SELECT id FROM users WHERE LOWER(email) = %s", [target_email])
            if found_u:
                target_id = found_u["id"]

        if not target_id:
            return api_response({"success": False, "message": "User not found to add"}, 404)

        if fetch_one("SELECT id FROM group_members WHERE group_id = %s AND user_id = %s", [group_id, target_id]):
            return api_response({"success": False, "message": "User is already in group"}, 400)

        execute("INSERT INTO group_members (group_id, user_id, role) VALUES (%s, %s, 'member')", [group_id, target_id])
        return api_response({"success": True, "message": "Member added successfully"})

    return method_not_allowed()


def group_member_detail(request, group_id, target_user_id):
    if request.method != "DELETE":
        return method_not_allowed()
    
    user, error = auth_user(request)
    if error:
        return error

    group = fetch_one("SELECT created_by FROM community_groups WHERE id = %s", [group_id])
    if not group:
        return api_response({"success": False, "message": "Group not found"}, 404)

    my_rec = fetch_one("SELECT role FROM group_members WHERE group_id = %s AND user_id = %s", [group_id, user["id"]])
    is_self = user["id"] == target_user_id
    is_admin = group["created_by"] == user["id"] or (my_rec and my_rec.get("role") in ["admin", "co-admin"]) or user.get("role") == "admin"

    if not is_self and not is_admin:
        return api_response({"success": False, "message": "Not authorized to remove member"}, 403)

    execute("DELETE FROM group_members WHERE group_id = %s AND user_id = %s", [group_id, target_user_id])
    return api_response({"success": True, "message": "Member removed"})


def group_member_role(request, group_id, target_user_id):
    if request.method != "PUT":
        return method_not_allowed()
    
    user, error = auth_user(request)
    if error:
        return error

    group = fetch_one("SELECT created_by FROM community_groups WHERE id = %s", [group_id])
    if not group:
        return api_response({"success": False, "message": "Group not found"}, 404)

    my_rec = fetch_one("SELECT role FROM group_members WHERE group_id = %s AND user_id = %s", [group_id, user["id"]])
    is_admin = group["created_by"] == user["id"] or (my_rec and my_rec.get("role") in ["admin", "co-admin"]) or user.get("role") == "admin"
    if not is_admin:
        return api_response({"success": False, "message": "Only admins can manage roles"}, 403)

    data = read_data(request)
    new_role = data.get("role") or "co-admin"
    if new_role not in ["admin", "co-admin", "member"]:
        new_role = "co-admin"

    execute("UPDATE group_members SET role = %s WHERE group_id = %s AND user_id = %s", [new_role, group_id, target_user_id])
    return api_response({"success": True, "message": f"Role updated to {new_role}"})


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
    execute("INSERT INTO group_members (group_id, user_id, role) VALUES (%s, %s, 'member')", [group_id, user["id"]])
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
            SELECT m.*, u.name as user_name, u.avatar_url as user_avatar, gm.role as member_role
            FROM messages m
            LEFT JOIN users u ON m.user_id = u.id
            LEFT JOIN group_members gm ON gm.group_id = m.group_id AND gm.user_id = m.user_id
            WHERE m.group_id = %s
            ORDER BY m.created_at ASC
            """,
            [group_id],
        )
        if rows:
            msg_ids = [m["id"] for m in rows]
            placeholders = ", ".join(["%s"] * len(msg_ids))
            all_reactions = fetch_all(
                f"""
                SELECT message_id, emoji, COUNT(*) as count,
                       SUM(CASE WHEN user_id = %s THEN 1 ELSE 0 END) as reacted_by_me
                FROM message_reactions
                WHERE message_id IN ({placeholders})
                GROUP BY message_id, emoji
                """,
                [user["id"]] + msg_ids,
            )
            reactions_by_msg = {}
            for r in all_reactions:
                reactions_by_msg.setdefault(r["message_id"], []).append(r)
            for msg in rows:
                msg["reactions"] = reactions_by_msg.get(msg["id"], [])
        return api_response({"success": True, "data": rows})

    if request.method == "POST":
        if not fetch_one("SELECT id FROM community_groups WHERE id = %s", [group_id]):
            return api_response({"success": False, "message": "Group not found"}, 404)
        if not fetch_one("SELECT id FROM group_members WHERE group_id = %s AND user_id = %s", [group_id, user["id"]]):
            execute("INSERT INTO group_members (group_id, user_id, role) VALUES (%s, %s, 'member')", [group_id, user["id"]])
        data = read_data(request)
        content = (data.get("content") or "").strip()
        image_url = data.get("image_url") or None
        if "image" in request.FILES:
            try:
                image_url = save_upload(request.FILES["image"], "messages")
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
            SELECT m.*, u.name as user_name, u.avatar_url as user_avatar, gm.role as member_role
            FROM messages m
            LEFT JOIN users u ON m.user_id = u.id
            LEFT JOIN group_members gm ON gm.group_id = m.group_id AND gm.user_id = m.user_id
            WHERE m.id = %s
            """,
            [message_id],
        )
        row["reactions"] = []
        return api_response({"success": True, "data": row}, 201)

    return method_not_allowed()


def message_detail(request, message_id):
    user, error = auth_user(request)
    if error:
        return error

    msg = fetch_one("SELECT * FROM messages WHERE id = %s", [message_id])
    if not msg:
        return api_response({"success": False, "message": "Message not found"}, 404)

    is_author = int(msg["user_id"]) == int(user["id"])
    is_superadmin = user.get("role") == "admin"
    is_circle_admin = bool(
        fetch_one(
            "SELECT id FROM group_members WHERE group_id = %s AND user_id = %s AND role IN ('admin', 'co-admin')",
            [msg["group_id"], user["id"]],
        )
        or fetch_one(
            "SELECT id FROM community_groups WHERE id = %s AND created_by = %s",
            [msg["group_id"], user["id"]],
        )
    )

    if request.method == "PUT" or request.method == "PATCH":
        if not is_author:
            return api_response({"success": False, "message": "Only the original author can edit this message"}, 403)
        data = read_data(request)
        content = (data.get("content") or "").strip()
        if not content and not msg.get("image_url"):
            return api_response({"success": False, "message": "Message content cannot be empty"}, 400)
        execute("UPDATE messages SET content = %s WHERE id = %s", [content, message_id])
        updated = fetch_one(
            """
            SELECT m.*, u.name as user_name, u.avatar_url as user_avatar, gm.role as member_role
            FROM messages m
            LEFT JOIN users u ON m.user_id = u.id
            LEFT JOIN group_members gm ON gm.group_id = m.group_id AND gm.user_id = m.user_id
            WHERE m.id = %s
            """,
            [message_id],
        )
        return api_response({"success": True, "message": "Message updated", "data": updated})

    if request.method == "DELETE":
        if not (is_author or is_superadmin or is_circle_admin):
            return api_response({"success": False, "message": "Permission denied to delete this message"}, 403)
        execute("DELETE FROM message_reactions WHERE message_id = %s", [message_id])
        execute("DELETE FROM messages WHERE id = %s", [message_id])
        return api_response({"success": True, "message": "Message deleted"})

    return method_not_allowed()


def toggle_message_reaction(request, message_id):
    if request.method != "POST":
        return method_not_allowed()

    user, error = auth_user(request)
    if error:
        return error

    if not fetch_one("SELECT id FROM messages WHERE id = %s", [message_id]):
        return api_response({"success": False, "message": "Message not found"}, 404)

    data = read_data(request)
    emoji = (data.get("emoji") or "👍").strip()

    try:
        # Enforce single emoji reaction per user per message
        existing = fetch_one(
            "SELECT id, emoji FROM message_reactions WHERE message_id = %s AND user_id = %s",
            [message_id, user["id"]],
        )
        if existing:
            if existing["emoji"] == emoji:
                # Same emoji clicked again -> remove reaction (toggle off)
                execute("DELETE FROM message_reactions WHERE id = %s", [existing["id"]])
                action = "removed"
            else:
                # Different emoji clicked -> swap/update to new emoji
                execute("UPDATE message_reactions SET emoji = %s WHERE id = %s", [emoji, existing["id"]])
                action = "swapped"
        else:
            # First reaction on this message
            execute(
                "INSERT INTO message_reactions (message_id, user_id, emoji) VALUES (%s, %s, %s)",
                [message_id, user["id"], emoji],
            )
            action = "added"
    except Exception:
        action = "updated"

    reactions = fetch_all(
        """
        SELECT emoji, COUNT(*) as count,
               SUM(CASE WHEN user_id = %s THEN 1 ELSE 0 END) as reacted_by_me
        FROM message_reactions
        WHERE message_id = %s
        GROUP BY emoji
        """,
        [user["id"], message_id],
    )

    return api_response({"success": True, "action": action, "reactions": reactions})


def is_google_form_url(url):
    if not url or not isinstance(url, str):
        return False
    u = url.strip().lower()
    return u.startswith("http://") or u.startswith("https://") or "docs.google.com" in u or "forms.gle" in u or "." in u


def events(request):
    if request.method == "GET":
        rows = fetch_all(
            """
            SELECT e.*, s.name as space_name, u.name as creator_name,
              (SELECT COUNT(*) FROM event_registrations WHERE event_id = e.id AND (status IS NULL OR LOWER(status) != 'rejected')) as participant_count
            FROM events e
            LEFT JOIN spaces s ON e.space_id = s.id
            JOIN users u ON e.created_by = u.id
            ORDER BY 
              CASE WHEN COALESCE(e.end_date, e.event_date) >= CURRENT_TIMESTAMP THEN 0 ELSE 1 END ASC,
              CASE WHEN COALESCE(e.end_date, e.event_date) >= CURRENT_TIMESTAMP THEN e.event_date END ASC,
              e.event_date DESC
            """
        )
        user, _ = auth_user(request)
        user_regs = fetch_all("SELECT event_id, status FROM event_registrations WHERE user_id = %s", [user["id"]]) if user else []
        reg_map = {r["event_id"]: (r.get("status") or "pending") for r in user_regs}
        for row in rows:
            if row["id"] in reg_map:
                row["my_status"] = reg_map[row["id"]]
            row["is_host"] = bool(user and (user.get("role") == "admin" or str(row.get("created_by")) == str(user.get("id"))))
        return api_response({"success": True, "count": len(rows), "data": rows})

    if request.method == "POST":
        user, error = auth_user(request)
        if error:
            return error
        data = read_data(request)
        missing = require_fields(data, ["title", "description", "eventDate"])
        if missing:
            return missing
        
        google_form_url = (data.get("googleFormUrl") or data.get("google_form_url") or "").strip()
        if google_form_url and not is_google_form_url(google_form_url):
            return api_response({"success": False, "message": "Please enter a valid Registration / External Link URL (e.g. https://...)"}, 400)

        if data.get("endDate") and data.get("endDate") < data.get("eventDate"):
            return api_response({"success": False, "message": "End date and time cannot be earlier than start time"}, 400)
        try:
            image_url = save_upload(request.FILES["image"], "events") if "image" in request.FILES else None
        except ValueError as exc:
            return api_response({"success": False, "message": str(exc)}, 400)
        
        is_paid = 1 if str(data.get("is_paid", "")).lower() in ["true", "1", "paid"] or (data.get("price") and float(data.get("price") or 0) > 0) else 0
        try:
            price = float(data.get("price") or 0) if is_paid else 0.0
        except (ValueError, TypeError):
            price = 0.0

        try:
            total_seats = int(data.get("total_seats") or data.get("totalSeats") or 50)
            if total_seats < 1:
                total_seats = 50
        except (ValueError, TypeError):
            total_seats = 50

        space_id = data.get("spaceId") or None
        event_id = None
        try:
            _, event_id = execute(
                """
                INSERT INTO events (title, city, venue, event_type, description, google_form_url, is_paid, price, total_seats, event_date, end_date, image_url, space_id, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                [
                    data.get("title"),
                    data.get("city") or None,
                    data.get("venue") or None,
                    data.get("eventType") or None,
                    data.get("description"),
                    google_form_url,
                    is_paid,
                    price,
                    total_seats,
                    data.get("eventDate"),
                    data.get("endDate") or None,
                    image_url,
                    space_id,
                    user["id"],
                ],
            )
        except Exception:
            try:
                if connection.vendor == "postgresql":
                    execute("ALTER TABLE events ADD COLUMN IF NOT EXISTS is_paid BOOLEAN DEFAULT FALSE")
                    execute("ALTER TABLE events ADD COLUMN IF NOT EXISTS price NUMERIC(10,2) DEFAULT 0")
                    execute("ALTER TABLE events ADD COLUMN IF NOT EXISTS total_seats INT DEFAULT 50")
                elif connection.vendor == "sqlite":
                    execute("ALTER TABLE events ADD COLUMN is_paid INTEGER DEFAULT 0")
                    execute("ALTER TABLE events ADD COLUMN price NUMERIC DEFAULT 0")
                    execute("ALTER TABLE events ADD COLUMN total_seats INTEGER DEFAULT 50")
                else:
                    execute("ALTER TABLE events ADD COLUMN is_paid BOOLEAN DEFAULT FALSE")
                    execute("ALTER TABLE events ADD COLUMN price DECIMAL(10,2) DEFAULT 0")
                    execute("ALTER TABLE events ADD COLUMN total_seats INT DEFAULT 50")

                _, event_id = execute(
                    """
                    INSERT INTO events (title, city, venue, event_type, description, google_form_url, is_paid, price, total_seats, event_date, end_date, image_url, space_id, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    [
                        data.get("title"),
                        data.get("city") or None,
                        data.get("venue") or None,
                        data.get("eventType") or None,
                        data.get("description"),
                        google_form_url,
                        is_paid,
                        price,
                        total_seats,
                        data.get("eventDate"),
                        data.get("endDate") or None,
                        image_url,
                        space_id,
                        user["id"],
                    ],
                )
            except Exception:
                _, event_id = execute(
                    """
                    INSERT INTO events (title, city, venue, event_type, description, google_form_url, event_date, end_date, image_url, space_id, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    [
                        data.get("title"),
                        data.get("city") or None,
                        data.get("venue") or None,
                        data.get("eventType") or None,
                        data.get("description"),
                        google_form_url,
                        data.get("eventDate"),
                        data.get("endDate") or None,
                        image_url,
                        space_id,
                        user["id"],
                    ],
                )

        return api_response({"success": True, "data": {"id": event_id, "title": data.get("title"), "google_form_url": google_form_url, "is_paid": is_paid, "price": price, "total_seats": total_seats, "eventDate": data.get("eventDate")}}, 201)

    return method_not_allowed()


def event_detail(request, event_id):
    event = fetch_one(
        """
        SELECT e.*, s.name as space_name, u.name as creator_name,
          (SELECT COUNT(*) FROM event_registrations WHERE event_id = e.id AND (status IS NULL OR LOWER(status) != 'rejected')) as participant_count
        FROM events e
        LEFT JOIN spaces s ON e.space_id = s.id
        JOIN users u ON e.created_by = u.id
        WHERE e.id = %s
        """,
        [event_id],
    )
    if not event:
        return api_response({"success": False, "message": "Event not found"}, 404)

    if request.method == "GET":
        user, _ = auth_user(request)
        if user:
            reg = fetch_one("SELECT status FROM event_registrations WHERE event_id = %s AND user_id = %s", [event_id, user["id"]])
            if reg:
                event["my_status"] = reg.get("status") or "pending"
        event["is_host"] = bool(user and (user.get("role") == "admin" or str(event.get("created_by")) == str(user.get("id"))))
        return api_response({"success": True, "data": event})

    if request.method == "PUT":
        user, error = auth_user(request)
        if error:
            return error

        if user.get("role") != "admin" and event["created_by"] != user["id"]:
            return api_response({"success": False, "message": "Only the event host or admin can edit this event"}, 403)

        data = read_data(request)
        title = data.get("title") or event.get("title")
        city = data.get("city") if "city" in data else event.get("city")
        venue = data.get("venue") if "venue" in data else event.get("venue")
        event_type = data.get("eventType") or data.get("event_type") or event.get("event_type")
        description = data.get("description") if "description" in data else event.get("description")
        
        google_form_url = (data.get("googleFormUrl") or data.get("google_form_url") if "googleFormUrl" in data or "google_form_url" in data else event.get("google_form_url") or "").strip()
        if google_form_url and not is_google_form_url(google_form_url):
            return api_response({"success": False, "message": "Please enter a valid Registration / External Link URL"}, 400)

        is_paid = event.get("is_paid", 0)
        if "is_paid" in data or "price" in data:
            is_paid = 1 if str(data.get("is_paid", "")).lower() in ["true", "1", "paid"] or (data.get("price") and float(data.get("price") or 0) > 0) else 0
        
        price = event.get("price", 0.0)
        if "price" in data:
            try:
                price = float(data.get("price") or 0) if is_paid else 0.0
            except (ValueError, TypeError):
                price = 0.0
        elif not is_paid:
            price = 0.0

        total_seats = event.get("total_seats", 50)
        if "total_seats" in data or "totalSeats" in data:
            try:
                total_seats = int(data.get("total_seats") or data.get("totalSeats") or 50)
                if total_seats < 1:
                    total_seats = 50
            except (ValueError, TypeError):
                total_seats = 50

        event_date = data.get("eventDate") or data.get("event_date") or event.get("event_date")
        end_date = data.get("endDate") or data.get("end_date") or event.get("end_date")

        image_url = event.get("image_url")
        if "image" in request.FILES:
            try:
                image_url = save_upload(request.FILES["image"], "events")
            except Exception as e:
                return api_response({"success": False, "message": str(e)}, 400)
        elif data.get("image_url"):
            image_url = data.get("image_url")

        try:
            execute(
                """
                UPDATE events 
                SET title = %s, city = %s, venue = %s, event_type = %s, description = %s, google_form_url = %s, is_paid = %s, price = %s, total_seats = %s, event_date = %s, end_date = %s, image_url = %s
                WHERE id = %s
                """,
                [title, city, venue, event_type, description, google_form_url, is_paid, price, total_seats, event_date, end_date, image_url, event_id],
            )
        except Exception:
            execute(
                """
                UPDATE events 
                SET title = %s, city = %s, venue = %s, event_type = %s, description = %s, google_form_url = %s, event_date = %s, end_date = %s, image_url = %s
                WHERE id = %s
                """,
                [title, city, venue, event_type, description, google_form_url, event_date, end_date, image_url, event_id],
            )

        return api_response({"success": True, "message": "Event updated successfully", "data": {"id": event_id, "title": title}})

    if request.method == "DELETE":
        user, error = auth_user(request)
        if error:
            return error

        if user.get("role") != "admin" and event["created_by"] != user["id"]:
            return api_response({"success": False, "message": "Only the event host or admin can delete this event"}, 403)

        execute("DELETE FROM events WHERE id = %s", [event_id])
        return api_response({"success": True, "message": "Event deleted successfully"})

    return method_not_allowed()


def register_event(request, event_id):
    if request.method != "POST":
        return method_not_allowed()
    user, error = auth_user(request)
    if error:
        return error
    event = fetch_one("SELECT id, google_form_url FROM events WHERE id = %s", [event_id])
    if not event:
        return api_response({"success": False, "message": "Event not found"}, 404)

    count_row = fetch_one(
        "SELECT COUNT(*) as active_count FROM event_registrations WHERE event_id = %s AND (status IS NULL OR LOWER(status) != 'rejected')",
        [event_id]
    )
    active_count = count_row.get("active_count", 0) if count_row else 0

    existing = fetch_one("SELECT id, COALESCE(status, 'pending') as status FROM event_registrations WHERE event_id = %s AND user_id = %s", [event_id, user["id"]])
    if existing:
        st = existing.get("status", "pending")
        return api_response({
            "success": True,
            "message": f"Your attendance request is {st.upper()}.",
            "status": st,
            "participant_count": active_count
        }, 200)

    if active_count >= 50:
        return api_response({"success": False, "message": "Sorry, this event is fully booked! 0 spots remaining."}, 400)

    execute("INSERT INTO event_registrations (event_id, user_id, status) VALUES (%s, %s, 'pending')", [event_id, user["id"]])
    new_count = active_count + 1
    return api_response({
        "success": True,
        "message": "Your attendance request is PENDING organizer review.",
        "status": "pending",
        "participant_count": new_count
    })


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
        SELECT r.id as registration_id, u.id as user_id, u.name, u.email, u.avatar_url,
               COALESCE(r.status, 'pending') as status, r.registered_at
        FROM event_registrations r
        JOIN users u ON r.user_id = u.id
        WHERE r.event_id = %s
        ORDER BY (CASE WHEN r.status = 'pending' THEN 1 WHEN r.status = 'approved' THEN 2 ELSE 3 END), r.registered_at DESC
        """,
        [event_id],
    )
    return api_response({"success": True, "count": len(rows), "data": rows})


def update_registration_status(request, event_id, target_user_id):
    if request.method != "PUT":
        return method_not_allowed()
    user, error = auth_user(request)
    if error:
        return error

    event = fetch_one("SELECT created_by FROM events WHERE id = %s", [event_id])
    if not event:
        return api_response({"success": False, "message": "Event not found"}, 404)

    if user.get("role") != "admin" and event["created_by"] != user["id"]:
        return api_response({"success": False, "message": "Only event host or admin can update registration status"}, 403)

    data = read_data(request)
    new_status = (data.get("status") or "").strip().lower()
    if new_status not in ["pending", "approved", "confirmed", "rejected"]:
        return api_response({"success": False, "message": "Invalid status value. Choose pending, approved, or rejected."}, 400)

    execute("UPDATE event_registrations SET status = %s WHERE event_id = %s AND user_id = %s", [new_status, event_id, target_user_id])
    return api_response({"success": True, "message": f"Participant status updated to {new_status.upper()}"})
