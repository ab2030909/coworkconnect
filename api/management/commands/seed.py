from django.core.management.base import BaseCommand

from api.schema import ensure_schema
from api.utils import execute, fetch_all


class Command(BaseCommand):
    help = "Seed CoWorkConnect with starter event data."

    def handle(self, *args, **options):
        ensure_schema()
        users = fetch_all("SELECT id FROM users LIMIT 1")
        if not users:
            self.stdout.write(self.style.WARNING("No users found. Register a user first, then run seed again."))
            return
        user_id = users[0]["id"]

        spaces = fetch_all("SELECT id FROM spaces LIMIT 1")
        if not spaces:
            execute(
                """
                INSERT INTO spaces (name, type, location, price_per_day, capacity, description)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                [
                    "Islamabad Innovation Hub",
                    "meeting_room",
                    "Islamabad",
                    5000,
                    50,
                    "Premium venue for community events.",
                ],
            )
            spaces = fetch_all("SELECT id FROM spaces LIMIT 1")

        space_id = spaces[0]["id"]
        events = [
            (
                "AWS Student Community Day 2026",
                "Big things are coming to Islamabad in 2026! AWS Student Community Day is back - bringing more knowledge, interactive workshops, valuable networking, and plenty of fun.",
                "2026-04-29 09:00:00",
            ),
            (
                "WordPress Meetup - Islamabad (FREE)",
                "Join the local WordPress community for a day of learning, sharing, and networking. Perfect for developers and designers alike.",
                "2026-05-16 14:00:00",
            ),
            (
                "Investors & Founders Community Meetup",
                "Join the biggest community of founders and investors in Pakistan. Direct networking and pitching opportunities.",
                "2026-04-23 15:00:00",
            ),
        ]

        for title, description, event_date in events:
            execute(
                "INSERT INTO events (title, description, event_date, space_id, created_by) VALUES (%s, %s, %s, %s, %s)",
                [title, description, event_date, space_id, user_id],
            )

        self.stdout.write(self.style.SUCCESS("Successfully added 3 starter events."))
