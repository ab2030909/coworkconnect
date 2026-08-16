from django.db import connection
import logging

_schema_checked = False
logger = logging.getLogger(__name__)


def ensure_schema():
    global _schema_checked
    if _schema_checked:
        return

    if connection.vendor == "sqlite":
        statements = sqlite_statements()
    elif connection.vendor == "postgresql":
        statements = postgres_statements()
    else:
        statements = mysql_statements()

    try:
        with connection.cursor() as cursor:
            for statement in statements:
                cursor.execute(statement)
            for statement in compatibility_statements(connection.vendor):
                try:
                    cursor.execute(statement)
                except Exception:
                    pass
    except Exception:
        logger.exception("Could not ensure database schema")
        return

    _schema_checked = True


def mysql_statements():
    return [
        """
        CREATE TABLE IF NOT EXISTS users (
          id INT AUTO_INCREMENT PRIMARY KEY,
          name VARCHAR(100) NOT NULL,
          email VARCHAR(100) NOT NULL UNIQUE,
          password VARCHAR(255) NOT NULL,
          role ENUM('user', 'admin') DEFAULT 'user',
          status VARCHAR(50) DEFAULT 'Available',
          bio TEXT,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS spaces (
          id INT AUTO_INCREMENT PRIMARY KEY,
          name VARCHAR(100) NOT NULL,
          type ENUM('desk', 'private_office', 'meeting_room', 'virtual_office') NOT NULL,
          location VARCHAR(100) DEFAULT 'General',
          price_per_day DECIMAL(10, 2) NOT NULL,
          rating DECIMAL(2, 1) DEFAULT 5.0,
          capacity INT NOT NULL,
          description TEXT,
          image_url VARCHAR(255),
          images TEXT,
          user_id INT,
          contact_email TEXT,
          contact_phone TEXT,
          website_url TEXT,
          is_available BOOLEAN DEFAULT TRUE,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS bookings (
          id INT AUTO_INCREMENT PRIMARY KEY,
          user_id INT NOT NULL,
          space_id INT NOT NULL,
          booking_date DATE NOT NULL,
          status ENUM('pending', 'confirmed', 'cancelled') DEFAULT 'pending',
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
          FOREIGN KEY (space_id) REFERENCES spaces(id) ON DELETE CASCADE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS posts (
          id INT AUTO_INCREMENT PRIMARY KEY,
          user_id INT NOT NULL,
          content TEXT NOT NULL,
          tags VARCHAR(255),
          image_url VARCHAR(255),
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS comments (
          id INT AUTO_INCREMENT PRIMARY KEY,
          post_id INT NOT NULL,
          user_id INT NOT NULL,
          parent_id INT DEFAULT NULL,
          content TEXT NOT NULL,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
          FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
          FOREIGN KEY (parent_id) REFERENCES comments(id) ON DELETE CASCADE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS comment_likes (
          id INT AUTO_INCREMENT PRIMARY KEY,
          comment_id INT NOT NULL,
          user_id INT NOT NULL,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          UNIQUE KEY unique_comment_like (comment_id, user_id),
          FOREIGN KEY (comment_id) REFERENCES comments(id) ON DELETE CASCADE,
          FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS post_likes (
          id INT AUTO_INCREMENT PRIMARY KEY,
          post_id INT NOT NULL,
          user_id INT NOT NULL,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          UNIQUE KEY unique_post_like (post_id, user_id),
          FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
          FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS community_groups (
          id INT AUTO_INCREMENT PRIMARY KEY,
          name VARCHAR(100) NOT NULL,
          description TEXT,
          created_by INT NOT NULL,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS group_members (
          id INT AUTO_INCREMENT PRIMARY KEY,
          group_id INT NOT NULL,
          user_id INT NOT NULL,
          joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          UNIQUE KEY unique_group_member (group_id, user_id),
          FOREIGN KEY (group_id) REFERENCES community_groups(id) ON DELETE CASCADE,
          FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS messages (
          id INT AUTO_INCREMENT PRIMARY KEY,
          group_id INT NOT NULL,
          user_id INT NOT NULL,
          content TEXT NOT NULL,
          image_url VARCHAR(255),
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (group_id) REFERENCES community_groups(id) ON DELETE CASCADE,
          FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS events (
          id INT AUTO_INCREMENT PRIMARY KEY,
          title VARCHAR(255) NOT NULL,
          city VARCHAR(100),
          venue VARCHAR(255),
          event_type VARCHAR(100),
          description TEXT,
          event_date DATETIME NOT NULL,
          end_date DATETIME,
          image_url VARCHAR(255),
          space_id INT,
          created_by INT NOT NULL,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (space_id) REFERENCES spaces(id) ON DELETE SET NULL,
          FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS event_registrations (
          id INT AUTO_INCREMENT PRIMARY KEY,
          event_id INT NOT NULL,
          user_id INT NOT NULL,
          registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          UNIQUE KEY unique_event_registration (event_id, user_id),
          FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
          FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """,
    ]


def sqlite_statements():
    return [
        """
        CREATE TABLE IF NOT EXISTS users (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          name TEXT NOT NULL,
          email TEXT NOT NULL UNIQUE,
          password TEXT NOT NULL,
          role TEXT DEFAULT 'user',
          status TEXT DEFAULT 'Available',
          bio TEXT,
          avatar_url TEXT,
          expertise TEXT,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS spaces (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          name TEXT NOT NULL,
          type TEXT NOT NULL,
          location TEXT DEFAULT 'General',
          price_per_day REAL NOT NULL,
          rating REAL DEFAULT 5.0,
          capacity INTEGER NOT NULL,
          description TEXT,
          image_url TEXT,
          images TEXT,
          user_id INTEGER,
          contact_email TEXT,
          contact_phone TEXT,
          website_url TEXT,
          is_available INTEGER DEFAULT 1,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS bookings (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INTEGER NOT NULL,
          space_id INTEGER NOT NULL,
          booking_date TEXT NOT NULL,
          status TEXT DEFAULT 'pending',
          created_at TEXT DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
          FOREIGN KEY (space_id) REFERENCES spaces(id) ON DELETE CASCADE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS posts (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INTEGER NOT NULL,
          content TEXT NOT NULL,
          tags TEXT,
          image_url TEXT,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS comments (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          post_id INTEGER NOT NULL,
          user_id INTEGER NOT NULL,
          parent_id INTEGER DEFAULT NULL,
          content TEXT NOT NULL,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
          FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
          FOREIGN KEY (parent_id) REFERENCES comments(id) ON DELETE CASCADE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS comment_likes (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          comment_id INTEGER NOT NULL,
          user_id INTEGER NOT NULL,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP,
          UNIQUE (comment_id, user_id),
          FOREIGN KEY (comment_id) REFERENCES comments(id) ON DELETE CASCADE,
          FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS post_likes (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          post_id INTEGER NOT NULL,
          user_id INTEGER NOT NULL,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP,
          UNIQUE (post_id, user_id),
          FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
          FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS community_groups (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          name TEXT NOT NULL,
          description TEXT,
          created_by INTEGER NOT NULL,
          image_url TEXT,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS group_members (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          group_id INTEGER NOT NULL,
          user_id INTEGER NOT NULL,
          joined_at TEXT DEFAULT CURRENT_TIMESTAMP,
          UNIQUE (group_id, user_id),
          FOREIGN KEY (group_id) REFERENCES community_groups(id) ON DELETE CASCADE,
          FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS messages (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          group_id INTEGER NOT NULL,
          user_id INTEGER NOT NULL,
          content TEXT NOT NULL,
          image_url TEXT,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (group_id) REFERENCES community_groups(id) ON DELETE CASCADE,
          FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS events (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          title TEXT NOT NULL,
          city TEXT,
          venue TEXT,
          event_type TEXT,
          description TEXT,
          event_date TEXT NOT NULL,
          end_date TEXT,
          image_url TEXT,
          space_id INTEGER,
          created_by INTEGER NOT NULL,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (space_id) REFERENCES spaces(id) ON DELETE SET NULL,
          FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS event_registrations (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          event_id INTEGER NOT NULL,
          user_id INTEGER NOT NULL,
          registered_at TEXT DEFAULT CURRENT_TIMESTAMP,
          UNIQUE (event_id, user_id),
          FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
          FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """,
    ]


def postgres_statements():
    return [
        """
        CREATE TABLE IF NOT EXISTS users (
          id SERIAL PRIMARY KEY,
          name VARCHAR(100) NOT NULL,
          email VARCHAR(100) NOT NULL UNIQUE,
          password VARCHAR(255) NOT NULL,
          role VARCHAR(20) DEFAULT 'user',
          status VARCHAR(50) DEFAULT 'Available',
          bio TEXT,
          avatar_url TEXT,
          expertise TEXT,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS spaces (
          id SERIAL PRIMARY KEY,
          name VARCHAR(100) NOT NULL,
          type VARCHAR(40) NOT NULL,
          location VARCHAR(100) DEFAULT 'General',
          price_per_day NUMERIC(10, 2) NOT NULL,
          rating NUMERIC(2, 1) DEFAULT 5.0,
          capacity INTEGER NOT NULL,
          description TEXT,
          image_url VARCHAR(255),
          images TEXT,
          user_id INTEGER,
          contact_email TEXT,
          contact_phone TEXT,
          website_url TEXT,
          is_available BOOLEAN DEFAULT TRUE,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS bookings (
          id SERIAL PRIMARY KEY,
          user_id INTEGER NOT NULL,
          space_id INTEGER NOT NULL,
          booking_date DATE NOT NULL,
          status VARCHAR(20) DEFAULT 'pending',
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
          FOREIGN KEY (space_id) REFERENCES spaces(id) ON DELETE CASCADE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS posts (
          id SERIAL PRIMARY KEY,
          user_id INTEGER NOT NULL,
          content TEXT NOT NULL,
          tags VARCHAR(255),
          image_url VARCHAR(255),
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS comments (
          id SERIAL PRIMARY KEY,
          post_id INTEGER NOT NULL,
          user_id INTEGER NOT NULL,
          parent_id INTEGER DEFAULT NULL,
          content TEXT NOT NULL,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
          FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
          FOREIGN KEY (parent_id) REFERENCES comments(id) ON DELETE CASCADE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS comment_likes (
          id SERIAL PRIMARY KEY,
          comment_id INTEGER NOT NULL,
          user_id INTEGER NOT NULL,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          UNIQUE (comment_id, user_id),
          FOREIGN KEY (comment_id) REFERENCES comments(id) ON DELETE CASCADE,
          FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS post_likes (
          id SERIAL PRIMARY KEY,
          post_id INTEGER NOT NULL,
          user_id INTEGER NOT NULL,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          UNIQUE (post_id, user_id),
          FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
          FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS community_groups (
          id SERIAL PRIMARY KEY,
          name VARCHAR(100) NOT NULL,
          description TEXT,
          created_by INTEGER NOT NULL,
          image_url VARCHAR(255),
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS group_members (
          id SERIAL PRIMARY KEY,
          group_id INTEGER NOT NULL,
          user_id INTEGER NOT NULL,
          joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          UNIQUE (group_id, user_id),
          FOREIGN KEY (group_id) REFERENCES community_groups(id) ON DELETE CASCADE,
          FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS messages (
          id SERIAL PRIMARY KEY,
          group_id INTEGER NOT NULL,
          user_id INTEGER NOT NULL,
          content TEXT NOT NULL,
          image_url VARCHAR(255),
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (group_id) REFERENCES community_groups(id) ON DELETE CASCADE,
          FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS events (
          id SERIAL PRIMARY KEY,
          title VARCHAR(255) NOT NULL,
          city VARCHAR(100),
          venue VARCHAR(255),
          event_type VARCHAR(100),
          description TEXT,
          google_form_url VARCHAR(500),
          event_date TIMESTAMP NOT NULL,
          end_date TIMESTAMP,
          image_url VARCHAR(255),
          space_id INTEGER,
          created_by INTEGER NOT NULL,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (space_id) REFERENCES spaces(id) ON DELETE SET NULL,
          FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS event_registrations (
          id SERIAL PRIMARY KEY,
          event_id INTEGER NOT NULL,
          user_id INTEGER NOT NULL,
          status VARCHAR(50) DEFAULT 'pending',
          registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          UNIQUE (event_id, user_id),
          FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
          FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS friendships (
          id SERIAL PRIMARY KEY,
          user_id INTEGER NOT NULL,
          friend_id INTEGER NOT NULL,
          status VARCHAR(50) DEFAULT 'pending',
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          UNIQUE (user_id, friend_id),
          FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
          FOREIGN KEY (friend_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS message_reactions (
          id SERIAL PRIMARY KEY,
          message_id INTEGER NOT NULL,
          user_id INTEGER NOT NULL,
          emoji VARCHAR(20) NOT NULL,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          UNIQUE (message_id, user_id, emoji),
          FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE,
          FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """,
    ]


def compatibility_statements(vendor):
    if vendor == "postgresql":
        return [
            "ALTER TABLE messages ADD COLUMN IF NOT EXISTS image_url VARCHAR(255)",
            "ALTER TABLE comments ADD COLUMN IF NOT EXISTS parent_id INT DEFAULT NULL REFERENCES comments(id) ON DELETE CASCADE",
            "ALTER TABLE events ADD COLUMN IF NOT EXISTS google_form_url VARCHAR(500)",
            "ALTER TABLE event_registrations ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'pending'",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS github_url VARCHAR(255)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS linkedin_url VARCHAR(255)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_url VARCHAR(255)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS headline VARCHAR(255)",
            "ALTER TABLE spaces ADD COLUMN IF NOT EXISTS amenities TEXT",
            "ALTER TABLE spaces ADD COLUMN IF NOT EXISTS images TEXT",
            "ALTER TABLE spaces ADD COLUMN IF NOT EXISTS contact_email VARCHAR(255)",
            "ALTER TABLE spaces ADD COLUMN IF NOT EXISTS contact_phone VARCHAR(50)",
            "ALTER TABLE spaces ADD COLUMN IF NOT EXISTS website_url VARCHAR(255)",
            "ALTER TABLE spaces ADD COLUMN IF NOT EXISTS pricing_plans TEXT",
            "CREATE INDEX IF NOT EXISTS idx_posts_created ON posts(created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_posts_user ON posts(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_comments_post ON comments(post_id)",
            "CREATE INDEX IF NOT EXISTS idx_post_likes_composite ON post_likes(post_id, user_id)",
            "CREATE INDEX IF NOT EXISTS idx_messages_group ON messages(group_id, created_at)",
            "CREATE INDEX IF NOT EXISTS idx_spaces_avail_price ON spaces(is_available, price_per_day)",
            "CREATE INDEX IF NOT EXISTS idx_group_members_usr_grp ON group_members(user_id, group_id)",
            "CREATE INDEX IF NOT EXISTS idx_reactions_msg ON message_reactions(message_id)",
            "CREATE INDEX IF NOT EXISTS idx_comment_likes_composite ON comment_likes(comment_id, user_id)",
        ]
    if vendor == "sqlite":
        return [
            "ALTER TABLE messages ADD COLUMN image_url TEXT",
            "ALTER TABLE comments ADD COLUMN parent_id INTEGER DEFAULT NULL REFERENCES comments(id) ON DELETE CASCADE",
            "ALTER TABLE events ADD COLUMN google_form_url TEXT",
            "ALTER TABLE event_registrations ADD COLUMN status TEXT DEFAULT 'pending'",
            "ALTER TABLE users ADD COLUMN github_url TEXT",
            "ALTER TABLE users ADD COLUMN linkedin_url TEXT",
            "ALTER TABLE users ADD COLUMN avatar_url TEXT",
            "ALTER TABLE users ADD COLUMN headline TEXT",
            "ALTER TABLE spaces ADD COLUMN amenities TEXT",
            "ALTER TABLE spaces ADD COLUMN images TEXT",
            "ALTER TABLE spaces ADD COLUMN contact_email TEXT",
            "ALTER TABLE spaces ADD COLUMN contact_phone TEXT",
            "ALTER TABLE spaces ADD COLUMN website_url TEXT",
            "ALTER TABLE spaces ADD COLUMN pricing_plans TEXT",
            "CREATE INDEX IF NOT EXISTS idx_posts_created ON posts(created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_posts_user ON posts(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_comments_post ON comments(post_id)",
            "CREATE INDEX IF NOT EXISTS idx_post_likes_composite ON post_likes(post_id, user_id)",
            "CREATE INDEX IF NOT EXISTS idx_messages_group ON messages(group_id, created_at)",
            "CREATE INDEX IF NOT EXISTS idx_spaces_avail_price ON spaces(is_available, price_per_day)",
            "CREATE INDEX IF NOT EXISTS idx_group_members_usr_grp ON group_members(user_id, group_id)",
            "CREATE INDEX IF NOT EXISTS idx_reactions_msg ON message_reactions(message_id)",
            "CREATE INDEX IF NOT EXISTS idx_comment_likes_composite ON comment_likes(comment_id, user_id)",
        ]
    return [
        "ALTER TABLE messages ADD COLUMN image_url VARCHAR(255)",
        "ALTER TABLE comments ADD COLUMN parent_id INT DEFAULT NULL REFERENCES comments(id) ON DELETE CASCADE",
        "ALTER TABLE events ADD COLUMN google_form_url VARCHAR(500)",
        "ALTER TABLE event_registrations ADD COLUMN status VARCHAR(50) DEFAULT 'pending'",
        "ALTER TABLE users ADD COLUMN github_url VARCHAR(255)",
        "ALTER TABLE users ADD COLUMN linkedin_url VARCHAR(255)",
        "ALTER TABLE users ADD COLUMN avatar_url VARCHAR(255)",
        "ALTER TABLE users ADD COLUMN headline VARCHAR(255)",
        "ALTER TABLE spaces ADD COLUMN amenities TEXT",
        "ALTER TABLE spaces ADD COLUMN images TEXT",
        "ALTER TABLE spaces ADD COLUMN contact_email VARCHAR(255)",
        "ALTER TABLE spaces ADD COLUMN contact_phone VARCHAR(50)",
        "ALTER TABLE spaces ADD COLUMN website_url VARCHAR(255)",
        "ALTER TABLE spaces ADD COLUMN pricing_plans TEXT",
    ]
