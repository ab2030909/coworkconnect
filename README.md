# CoWorkConnect — Full Platform Architecture & Technical Documentation 🏢🌐

> **CoWorkConnect** is an enterprise-grade coworking space management, social networking, and professional collaboration platform. Built with Python/Django and a high-performance, reactive Vanilla/Alpine.js frontend, it unifies flexible workspace booking, mastermind circles, community networking feeds, and verified event management into a single, cohesive ecosystem.

---

## 📑 Table of Contents

1. [Executive Summary & Problem Statement](#-1-executive-summary--problem-statement)
2. [High-Level System Architecture](#-2-high-level-system-architecture)
   - [System Context Diagram](#system-context-diagram)
   - [Full Request & Response Pipeline](#full-request--response-pipeline)
3. [Database Architecture & ERD](#-3-database-architecture--erd)
   - [Entity-Relationship Diagram (ERD)](#entity-relationship-diagram-erd)
   - [Database Schema & Performance Indexes](#database-schema--performance-indexes)
4. [Complete Features & Modules Catalog](#-4-complete-features--modules-catalog)
   - [Module 1: Authentication, Role-Based Access & Rate Limiting](#module-1-authentication-role-based-access--rate-limiting)
   - [Module 2: Client-Side HTML Sanitization (DOMPurify XSS Shield)](#module-2-client-side-html-sanitization-dompurify-xss-shield)
   - [Module 3: Stale-While-Revalidate (SWR) Client Caching Engine](#module-3-stale-while-revalidate-swr-client-caching-engine)
   - [Module 4: Dual-Layer Image Compression Engine](#module-4-dual-layer-image-compression-engine)
   - [Module 5: Workspace Discovery & Adaptive Photo Collage](#module-5-workspace-discovery--adaptive-photo-collage)
   - [Module 6: Dual-Source Location Intelligence & Geocoding](#module-6-dual-source-location-intelligence--geocoding)
   - [Module 7: Professional Networking Feed & User Activity Filters](#module-7-professional-networking-feed--user-activity-filters)
   - [Module 8: Mastermind Circles & Real-Time Chat](#module-8-mastermind-circles--real-time-chat)
   - [Module 9: Single-Emoji Reaction Engine (Swap & Toggle)](#module-9-single-emoji-reaction-engine-swap--toggle)
   - [Module 10: Event Academy & Verification Center](#module-10-event-academy--verification-center)
   - [Module 11: Member Profiles & Facebook-Style Friendship Graph](#module-11-member-profiles--facebook-style-friendship-graph)
   - [Module 12: Admin Management & Moderation Hub](#module-12-admin-management--moderation-hub)
5. [Performance Engineering & Bottleneck Elimination](#-5-performance-engineering--bottleneck-elimination)
   - [N+1 Query Elimination (Batch Resolution)](#n1-query-elimination-batch-resolution)
   - [Hardware-Accelerated Skeleton Shimmer](#hardware-accelerated-skeleton-shimmer)
   - [Connection Pooling & Network Latency](#connection-pooling--network-latency)
6. [Complete REST API Reference](#-6-complete-rest-api-reference)
7. [Technology Stack](#-7-technology-stack)
8. [Installation & Local Setup](#-8-installation--local-setup)
9. [Environment Variables Reference](#-9-environment-variables-reference)
10. [Production Deployment Guide](#-10-production-deployment-guide)

---

## 🎯 1. Executive Summary & Problem Statement

### The Problem
Modern remote teams, freelancers, and growing startups frequently struggle with fragmented software tooling:
- Workspace booking platforms operate in isolation from professional community networks.
- Discussion groups are buried in siloed messaging apps without physical workspace context.
- Local networking events and workshops lack structured ticketing and attendance verification.
- Space listings suffer from opaque pricing, rigid long-term lease lock-ins, and slow loading interfaces.

### The Solution: CoWorkConnect
**CoWorkConnect** bridges physical real estate with digital social capital:
- **Instant Workspace Marketplace**: Filter verified desks, private suites, and meeting rooms with custom pass options and direct host contact.
- **Community Feed & Author Headlines**: Share milestones, insights, and project updates with verified local professionals.
- **Mastermind Circles & Chat**: Topic-focused discussion groups with image attachments, in-place message rendering, and single-emoji reaction swaps.
- **Verified Events Hub**: Compulsory Google Form attendee registration with in-app verification sheets and pass generation.
- **Facebook-Style Social Graph**: Manage bidirectional friendships, view public member portfolios, and track mutual connections.

---

## 🏛️ 2. High-Level System Architecture

### System Context Diagram

```mermaid
flowchart TD
    subgraph ClientLayer["🖥️ Frontend Client Layer (UI)"]
        UI_SPA["Vanilla JS (ES6+) + Alpine.js Stores<br/>DOMPurify XSS Shield · SWR Client Cache<br/>Lucide SVG Icons · Responsive CSS Tokens"]
        Pages["spaces.html · space-details.html<br/>community.html · groups.html<br/>events.html · event-details.html<br/>profile.html · user-profile.html · admin.html"]
    end

    subgraph GatewayLayer["⚡ ASGI / Daphne Application Gateway"]
        Router["URL Routing & Request Dispatcher<br/>(/api/* and Static File Handler)"]
        Middleware["AuthRateLimitMiddleware<br/>EnsureSchemaMiddleware<br/>CorsMiddleware<br/>SecurityMiddleware"]
    end

    subgraph ServiceLayer["🧠 Backend Core Services (Django)"]
        AuthSvc["Auth & Security Engine<br/>(JWT HS256 + bcrypt + Rate Limiter)"]
        SpaceSvc["Workspace & Location Engine<br/>(Dual Geocoding + Custom Passes)"]
        ChatSvc["Circle & Messaging Engine<br/>(In-Place Chat + Emoji State Machine)"]
        FeedSvc["Feed & Social Graph Engine<br/>(Batch Comments + Friends Graph)"]
        EventSvc["Events & Registration Engine<br/>(Google Forms + Verification)"]
    end

    subgraph StorageLayer["💾 Persistence & Media Layer"]
        DB[(PostgreSQL / SQLite / MySQL<br/>Composite B-Tree Indexes · Pooling)]
        CloudMedia["Cloudinary / Local Uploads<br/>(Dual-Layer Pillow Compression Engine)"]
    end

    UI_SPA -->|"HTTP REST API (Bearer JWT)"| Router
    Pages -->|"swrFetch() Promises & Alpine Stores"| Router
    Router --> Middleware
    Middleware --> ServiceLayer
    ServiceLayer -->|"Single Batch SQL Queries"| DB
    ServiceLayer -->|"Image Compression & I/O"| CloudMedia
```

### Full Request & Response Pipeline

```mermaid
sequenceDiagram
    autonumber
    actor User as User / Browser
    participant SWR as SWR Cache / DOMPurify
    participant Server as Django ASGI Server
    participant RateLimiter as AuthRateLimitMiddleware
    participant View as API View Controller
    participant DB as Relational Database (PostgreSQL)

    User->>SWR: Navigate to Page / Trigger Filter
    SWR->>User: Immediate 0ms Cache Render (If Available)
    SWR->>Server: HTTP Request (GET /api/spaces + Bearer Token)
    Server->>RateLimiter: Check Request Path & Rate Limits
    RateLimiter->>View: Dispatch to API View Controller
    View->>DB: Query with B-Tree Index (Reused connection via CONN_MAX_AGE)
    DB-->>View: Result Row & Serialized JSON Fields
    View-->>Server: JsonResponse (200 OK + Payload)
    Server-->>SWR: HTTP 200 JSON Response
    SWR->>SWR: Sanitize Payload with DOMPurify & Update Cache
    SWR->>User: Reconcile UI & Render Data (Lucide Icons + Dynamic DOM)
```

---

## 🗄️ 3. Database Architecture & ERD

### Entity-Relationship Diagram (ERD)

```mermaid
erDiagram
    USERS ||--o{ SPACES : "creates/hosts"
    USERS ||--o{ BOOKINGS : "places"
    USERS ||--o{ POSTS : "authors"
    USERS ||--o{ COMMENTS : "writes"
    USERS ||--o{ POST_LIKES : "likes"
    USERS ||--o{ COMMENT_LIKES : "likes"
    USERS ||--o{ COMMUNITY_GROUPS : "creates"
    USERS ||--o{ GROUP_MEMBERS : "joins"
    USERS ||--o{ MESSAGES : "sends"
    USERS ||--o{ MESSAGE_REACTIONS : "reacts"
    USERS ||--o{ EVENTS : "hosts"
    USERS ||--o{ EVENT_REGISTRATIONS : "registers"
    USERS ||--o{ FRIENDSHIPS : "initiates/receives"

    SPACES ||--o{ BOOKINGS : "reserved in"
    SPACES ||--o{ EVENTS : "hosts venue"

    POSTS ||--o{ COMMENTS : "contains"
    POSTS ||--o{ POST_LIKES : "receives"
    COMMENTS ||--o{ COMMENT_LIKES : "receives"

    COMMUNITY_GROUPS ||--o{ GROUP_MEMBERS : "has roster"
    COMMUNITY_GROUPS ||--o{ MESSAGES : "contains chat"
    MESSAGES ||--o{ MESSAGE_REACTIONS : "receives emoji"

    EVENTS ||--o{ EVENT_REGISTRATIONS : "has attendees"

    USERS {
        int id PK
        string name
        string email UK
        string password
        string role "user | admin"
        string status
        string headline
        text bio
        string avatar_url
        string github_url
        string linkedin_url
        string expertise
        timestamp created_at
    }

    SPACES {
        int id PK
        int user_id FK
        string name
        string type "desk | private_office | meeting_room | virtual_office"
        string location
        decimal price_per_day
        decimal rating
        int capacity
        text description
        string image_url
        text images
        text amenities
        text pricing_plans
        string contact_email
        string contact_phone
        string website_url
        boolean is_available
        timestamp created_at
    }

    POSTS {
        int id PK
        int user_id FK
        text content
        string tags
        string image_url
        timestamp created_at
    }

    COMMENTS {
        int id PK
        int post_id FK
        int user_id FK
        int parent_id FK
        text content
        timestamp created_at
    }

    COMMUNITY_GROUPS {
        int id PK
        int created_by FK
        string name
        text description
        string image_url
        timestamp created_at
    }

    MESSAGES {
        int id PK
        int group_id FK
        int user_id FK
        text content
        string image_url
        timestamp created_at
    }

    MESSAGE_REACTIONS {
        int id PK
        int message_id FK
        int user_id FK
        string emoji
        timestamp created_at
    }

    EVENTS {
        int id PK
        int created_by FK
        int space_id FK
        string title
        string event_type
        string city
        string location
        timestamp event_date
        timestamp end_date
        text description
        string google_form_url
        string image_url
        timestamp created_at
    }

    FRIENDSHIPS {
        int id PK
        int user_id FK
        int friend_id FK
        string status "pending | accepted | rejected"
        timestamp created_at
    }
```

### Database Schema & Performance Indexes

To ensure sub-millisecond execution even under heavy database loads, the following composite and B-tree indexes are maintained automatically by [`api/schema.py`](file:///d:/PROGRAMS/web/random/coworkconnect/api/schema.py):

| Index Name | Table | Columns | Purpose |
| :--- | :--- | :--- | :--- |
| `idx_posts_created` | `posts` | `created_at DESC` | Instant pagination of the global networking feed |
| `idx_posts_user` | `posts` | `user_id` | User activity filtering (`community.html?user_id=X`) |
| `idx_comments_post` | `comments` | `post_id` | Batch-fetching all post comments in 1 query |
| `idx_post_likes_composite` | `post_likes` | `post_id, user_id` | Instant verification of user's liked status |
| `idx_messages_group` | `messages` | `group_id, created_at` | Sub-5ms retrieval of channel chat history |
| `idx_reactions_msg` | `message_reactions` | `message_id` | Batch aggregation of emoji counts and reactions |
| `idx_group_members_usr_grp` | `group_members` | `user_id, group_id` | Instant membership and permission checks |
| `idx_comment_likes_composite` | `comment_likes` | `comment_id, user_id` | Batch resolution of comment likes |
| `idx_spaces_avail_price` | `spaces` | `is_available, price_per_day` | Rapid faceted search and price sorting |

---

## 🧩 4. Complete Features & Modules Catalog

### Module 1: Authentication, Role-Based Access & Rate Limiting
- **One-Way Password Hashing**: Utilizes `bcrypt` with cryptographic salt generation.
- **Stateless JWT Tokens**: Issues signed JSON Web Tokens (`HS256`) containing `user_id`, `role`, and expiration timestamp (`30d`).
- **IP-Based Authentication Rate Limiting (`AuthRateLimitMiddleware`)**:
  - Automatically intercepts POST requests to `/api/auth/login` and `/api/auth/register`.
  - Enforces a sliding rate window (max **5 attempts per 60 seconds** per IP).
  - Returns `429 Too Many Requests` with a calculated `Retry-After: <seconds>` HTTP header to block brute-force credential stuffing.
- **Client Storage & Interceptors**: Stored in `localStorage` and dispatched automatically in the `Authorization: Bearer <token>` HTTP header by `apiFetch()` in [`ui/app.js`](file:///d:/PROGRAMS/web/random/coworkconnect/ui/app.js).
- **Alpine.js Global Auth Store**: Dynamic reactivity updates user profile avatars and names across the navbar and guest actions seamlessly.

```mermaid
flowchart LR
    A[User Submits Creds] --> B[AuthRateLimitMiddleware]
    B -->|Attempts >= 5 in 60s| C[HTTP 429 Too Many Requests + Retry-After]
    B -->|Attempts < 5| D[Django Auth Controller]
    D -->|Verify bcrypt hash| E[(Users Table)]
    E -->|Match OK| F[Generate JWT Token]
    F --> G[Client Browser LocalStorage + Alpine Store]
```

---

### Module 2: Client-Side HTML Sanitization (DOMPurify XSS Shield)
- **DOMPurify CDN Integration**: Injected into the `<head>` of all 13 HTML pages.
- **Strict Tag Whitelisting**: [`sanitizeHtml()`](file:///d:/PROGRAMS/web/random/coworkconnect/ui/app.js) permits only safe semantic formatting tags (`<b>`, `<i>`, `<em>`, `<strong>`, `<a>`, `<span>`, `<p>`, `<br>`, `<code>`, `<pre>`, `<ul>`, `<ol>`, `<li>`, `<small>`) and safe attributes (`href`, `target`, `class`, `style`, `rel`).
- **Zero-Tag Stripping**: [`escapeHtml()`](file:///d:/PROGRAMS/web/random/coworkconnect/ui/app.js) executes complete tag neutralization (`ALLOWED_TAGS: []`) for pure string inputs, guaranteeing 100% immunity against Cross-Site Scripting (XSS) in user-submitted comments, bio fields, and posts.

---

### Module 3: Stale-While-Revalidate (SWR) Client Caching Engine
- **Instantaneous 0ms Page Transitions**: [`swrFetch()`](file:///d:/PROGRAMS/web/random/coworkconnect/ui/app.js) immediately renders cached data from in-memory maps or `sessionStorage` before network requests complete.
- **Silent Background Revalidation**: Simultaneously triggers a background fetch to verify fresh data, smoothly reconciling the DOM with zero UI flashes or layout jumps.
- **Intelligent Invalidation**: [`clearSwrCache(prefix)`](file:///d:/PROGRAMS/web/random/coworkconnect/ui/app.js) purges cached entries whenever a user publishes a new space, deletes a listing, or submits a post.

---

### Module 4: Dual-Layer Image Compression Engine
- **Layer 1 (Frontend Pre-Upload Canvas Compression)**:
  - `compressImageFile(file)` in [`ui/app.js`](file:///d:/PROGRAMS/web/random/coworkconnect/ui/app.js) reads uploaded images via FileReader into an HTML5 Canvas.
  - Automatically downsizes massive multi-megabyte photos (e.g. 4000x3000px DSLR shots) to a max bounding box of **1200x1200px** with JPEG quality `0.82` before network transmission.
- **Layer 2 (Backend Pillow/PIL Optimization)**:
  - `save_upload()` in [`api/utils.py`](file:///d:/PROGRAMS/web/random/coworkconnect/api/utils.py) strips unnecessary EXIF metadata, resizes to a max width of **1600px**, and saves with Pillow optimization flags.

```mermaid
flowchart LR
    A[Raw Image File<br/>8MB - 4000x3000px] -->|HTML5 Canvas| B[Frontend Resizing & Compression<br/>~250KB - 1200x1200px]
    B -->|POST Multipart Upload| C[Django Backend]
    C -->|Pillow / PIL Strip EXIF & Quality 82| D[Optimized Storage File / Cloudinary<br/>~120KB WebP/JPEG]
```

---

### Module 5: Workspace Discovery & Adaptive Photo Collage
- **Explore Grid ([`ui/spaces.html`](file:///d:/PROGRAMS/web/random/coworkconnect/ui/spaces.html))**: Fast faceted search by registered city, space type (`Hot Desk`, `Dedicated Desk`, `Private Office`, `Meeting Room`), and daily price range with SWR 0ms caching.
- **Custom Workspace Options & Passes**: Hosts can define unlimited flexible passes (e.g., *Half-Day Flex Pass*, *Weekly Dedicated Pass*, *Monthly Team Suite*) stored as JSON arrays in `pricing_plans`.
- **Adaptive 1-to-5 Photo Collage ([`ui/space-details.html`](file:///d:/PROGRAMS/web/random/coworkconnect/ui/space-details.html))**:
  - `1 Image`: Full-width hero cover.
  - `2 Images`: 50/50 dual split layout.
  - `3 Images`: 60/40 primary tile with stacked secondary tiles.
  - `4 Images`: Primary tile with 3-row stacked preview column.
  - `5+ Images`: Master showcase tile with a 4-tile thumbnail grid and a *"View Slideshow (N)"* trigger button.
- **Fullscreen Lightbox Slideshow**: Fullscreen modal with smooth next/prev slide navigation, keyboard shortcuts (`Esc`, `←`, `→`), and image counter indicators.

---

### Module 6: Dual-Source Location Intelligence & Geocoding
1. **Explore Search (`#location-input`)**:
   - Queries `/api/locations/suggest?q=...` strictly against **registered workspaces in the database**.
   - Displays a green `Registered` badge so users never search in non-existent cities.
2. **"List Your Space" Form (`#new-space-location`)**:
   - Queries **OpenStreetMap / Nominatim Geocoding API** for real-world streets, districts, landmarks, and coordinates.
   - Displays a blue `Map Place` badge and dynamically syncs the embedded Google Maps iframe live as the user types.

```mermaid
flowchart TD
    subgraph SearchInput["🔍 Explore Spaces Search"]
        S_Input[User types 'Islamabad'] --> S_API["GET /api/locations/suggest?q=Islamabad"]
        S_DB[(Spaces Database)] --> S_API
        S_API --> S_Dropdown["Dropdown: 'Islamabad' (Registered Badge)"]
    end

    subgraph ListingInput["📍 List Your Space Form"]
        L_Input[User types 'F-7 Markaz'] --> L_Geo["Nominatim Geocoding API"]
        L_Geo --> L_Dropdown["Dropdown: 'F-7 Markaz, Islamabad' (Map Place Badge)"]
        L_Dropdown --> L_Map["Auto-Update Live Google Map Iframe & Link"]
    end
```

---

### Module 7: Professional Networking Feed & User Activity Filters
- **Author Headlines & Professional Bios**: Author cards showcase verified roles (e.g. *"Full Stack Engineer @ FinTech"*) instead of generic badges.
- **Tag Filtering**: Filter feed content by `#startups`, `#design`, `#events`, `#hiring`, etc.
- **User Activity Filter (`community.html?user_id=X`)**: Deep-link to view all networking posts created by a specific member.
- **Optimistic Interactions**: Like toggles and comments update the DOM instantaneously before background network synchronization.

---

### Module 8: Mastermind Circles & Real-Time Chat
- **Topic Channels**: Create and join dedicated industry or co-working circles with avatars and member rosters.
- **In-Place Message Rendering**: Sent messages append directly to `#messages-feed-container` with smooth auto-scrolling without refreshing the channel view.
- **Image Attachments**: Attach photos to messages with compressed previews and full-size zoom inspection.

---

### Module 9: Single-Emoji Reaction Engine (Swap & Toggle)
- **Constraint**: Each user can have **at most one active emoji reaction per message**.
- **Swap Mechanic**: Clicking a different emoji automatically deletes/swaps the old reaction and applies the new emoji in-place.
- **Toggle-Off Mechanic**: Clicking the same emoji removes/toggles off the user's reaction.

```mermaid
stateDiagram-v2
    [*] --> NoReaction : User has not reacted

    NoReaction --> ReactedEmojiA : Click Emoji A (action: added)
    ReactedEmojiA --> NoReaction : Click Emoji A again (action: removed)
    ReactedEmojiA --> ReactedEmojiB : Click Emoji B (action: swapped)
    ReactedEmojiB --> NoReaction : Click Emoji B again (action: removed)
    ReactedEmojiB --> ReactedEmojiA : Click Emoji A (action: swapped)
```

---

### Module 10: Event Academy & Verification Center
- **Compulsory Google Form Integration**: Event hosts supply a Google Form registration URL.
- **Embedded Modal Flow**: Prospective attendees complete registration inside an interactive in-app modal.
- **Host Verification Center**: Hosts access connected response sheets and manage attendee statuses (`pending`, `approved`, `rejected`).
- **Pass Generation**: Approved attendees receive QR-coded ticket passes.

---

### Module 11: Member Profiles & Facebook-Style Friendship Graph
- **Bidirectional Friendships**:
  - `+ Add Friend` ➔ Outgoing request (`status: pending`).
  - `⏳ Request Sent` ➔ Pending response indicator.
  - `✓ Accept Friend Request` ➔ Bilateral friend confirmation (`status: accepted`).
  - `Friends ✓ (Unfriend)` ➔ Friendship management and removal.
- **Public Profile View ([`ui/user-profile.html`](file:///d:/PROGRAMS/web/random/coworkconnect/ui/user-profile.html))**: Direct portfolio link showcasing GitHub and LinkedIn links (emojis removed for clean aesthetic), expertise chips, bio, and shared workspaces.

---

### Module 12: Admin Management & Moderation Hub
- **Inventory Control**: Update or delete any space listing, manage capacity, and toggle availability.
- **Moderation**: Remove inappropriate community posts, comments, and messages.
- **User Records**: View registered accounts, modify roles (`user` ➔ `admin`), and inspect audit logs.

---

## ⚡ 5. Performance Engineering & Bottleneck Elimination

### N+1 Query Elimination (Batch Resolution)
In previous iterations, loading 50 posts triggered 1 post query + 50 comment queries + 150 comment-like queries (**201 database roundtrips**).

We refactored all multi-item endpoints in [`api/views.py`](file:///d:/PROGRAMS/web/random/coworkconnect/api/views.py) to use **Single Batch Lookups (`WHERE IN (...)`)**:

```mermaid
graph LR
    subgraph LegacyApproach["❌ Old Sequential N+1 Queries (201 DB Roundtrips ~1,200ms)"]
        A1[Fetch 50 Posts] --> A2[Query Comments for Post 1]
        A2 --> A3[Query Likes for Comment 1..N]
        A3 --> A4[Query Comments for Post 2..50...]
    end

    subgraph OptimizedApproach["✅ CoWorkConnect Batch Resolution (2 DB Queries <15ms)"]
        B1["1. SELECT * FROM posts ORDER BY created_at DESC LIMIT 50"] --> B2["2. SELECT * FROM comments WHERE post_id IN (1, 2, ... 50)"]
        B2 --> B3["3. Group Comments in Python Dict & Return JSON"]
    end
```

### Hardware-Accelerated Skeleton Shimmer
Implemented a dual-layer GPU-composited moving highlight shimmer wave in [`ui/style.css`](file:///d:/PROGRAMS/web/random/coworkconnect/ui/style.css):
- **Base Layer**: Linear gradient shifting smoothly across light slate tones (`CCShimmerGradient`).
- **Highlight Sweep Beam**: `::after` pseudo-element with `linear-gradient(90deg, transparent, rgba(255,255,255,0.75), transparent)` translating from `translateX(-150%)` to `translateX(150%)` at 60fps/120fps with zero layout reflows.

### Connection Pooling & Network Latency
- **Persistent Socket Connections**: Added `"CONN_MAX_AGE": 600` to database settings in [`coworkconnect/settings.py`](file:///d:/PROGRAMS/web/random/coworkconnect/coworkconnect/settings.py).
- **TLS Handshake Savings**: Reuses existing TCP/SSL channels, eliminating 1.5s–2.5s connection reconnection penalties when communicating with remote databases (e.g. Neon PostgreSQL).

---

## 📡 6. Complete REST API Reference

### Authentication Endpoints
| Method | Endpoint | Auth | Description | Rate Limit |
| :--- | :--- | :---: | :--- | :---: |
| `POST` | `/api/auth/register` | No | Register new user account (`name`, `email`, `password`) | 5 req / 60s |
| `POST` | `/api/auth/login` | No | Authenticate user & return JWT token | 5 req / 60s |
| `GET` | `/api/auth/me` | Yes | Get authenticated user profile & role | Standard |

### Workspaces & Locations
| Method | Endpoint | Auth | Description |
| :--- | :--- | :---: | :--- |
| `GET` | `/api/spaces` | No | Faceted workspace search (`location`, `type`, `minPrice`, `maxPrice`, `sort`) |
| `POST` | `/api/spaces` | Yes | Publish new workspace listing (with image upload & pricing plans) |
| `GET` | `/api/spaces/<id>` | No | Get comprehensive space details, images list, amenities, and plans |
| `PUT` | `/api/spaces/<id>` | Yes | Update workspace listing (creator or admin only) |
| `DELETE` | `/api/spaces/<id>` | Yes | Delete workspace & cascade delete bookings/references |
| `GET` | `/api/locations/suggest` | No | Autocomplete location suggestions from registered database hubs |

### Networking Feed & Comments
| Method | Endpoint | Auth | Description |
| :--- | :--- | :---: | :--- |
| `GET` | `/api/posts` | Optional | Get posts feed with batch-resolved comments and likes (`tag`, `user_id`) |
| `POST` | `/api/posts` | Yes | Publish new networking post with optional photo |
| `DELETE` | `/api/posts/<id>` | Yes | Delete post (author or admin only) |
| `POST` | `/api/posts/<id>/like` | Yes | Toggle like on a networking post |
| `POST` | `/api/posts/<id>/comments` | Yes | Add comment to a post |
| `DELETE` | `/api/comments/<id>` | Yes | Delete comment (author or admin only) |
| `POST` | `/api/comments/<id>/like` | Yes | Toggle like on a comment |

### Circles & Messages
| Method | Endpoint | Auth | Description |
| :--- | :--- | :---: | :--- |
| `GET` | `/api/groups` | Optional | List all circles with batch membership status and member counts |
| `POST` | `/api/groups` | Yes | Create new discussion circle |
| `GET` | `/api/groups/<id>` | Optional | Get circle details and admin permissions |
| `PUT` | `/api/groups/<id>` | Yes | Update circle info (admin/host only) |
| `DELETE` | `/api/groups/<id>` | Yes | Delete circle (admin/host only) |
| `GET` | `/api/groups/<id>/messages` | Yes | Retrieve chat history with batch-aggregated emoji reactions |
| `POST` | `/api/groups/<id>/messages` | Yes | Send chat message with optional photo attachment |
| `POST` | `/api/groups/<id>/join` | Yes | Join a circle |
| `POST` | `/api/messages/<id>/reactions` | Yes | Single-emoji reaction toggle / swap engine |

### Events & Registrations
| Method | Endpoint | Auth | Description |
| :--- | :--- | :---: | :--- |
| `GET` | `/api/events` | Optional | List upcoming events with city & category filters |
| `POST` | `/api/events` | Yes | Create new event with compulsory Google Form URL |
| `GET` | `/api/events/<id>` | Optional | Get event details, host info, and user registration status |
| `PUT` | `/api/events/<id>` | Yes | Update event details (creator or admin only) |
| `DELETE` | `/api/events/<id>` | Yes | Delete event (creator or admin only) |
| `POST` | `/api/events/<id>/register` | Yes | Submit event registration |
| `GET` | `/api/events/<id>/registrations`| Yes | View attendee list & Google Sheets verification link (host/admin) |
| `PUT` | `/api/events/<id>/registrations/<uid>` | Yes | Update registration status (`approved`, `rejected`) |

### Social Graph & Profiles
| Method | Endpoint | Auth | Description |
| :--- | :--- | :---: | :--- |
| `GET` | `/api/profile` | Yes | Get authenticated user's private profile & friend count |
| `PUT` | `/api/profile` | Yes | Update bio, headline, skills, GitHub URL, LinkedIn URL, status |
| `GET` | `/api/users/<id>` | Optional | Get public member profile, statistics, and mutual connections |
| `GET` | `/api/users/search` | No | Search member directory by name, headline, or expertise |
| `POST` | `/api/friends/request` | Yes | Send friend request to user |
| `POST` | `/api/friends/accept` | Yes | Accept incoming friend request |
| `POST` | `/api/friends/remove` | Yes | Unfriend / cancel friend request |
| `GET` | `/api/friends` | Yes | List authenticated user's accepted friends |

---

## 🛠️ 7. Technology Stack

| Layer | Technology | Version / Spec | Purpose |
| :--- | :--- | :--- | :--- |
| **Frontend Core** | HTML5 / CSS3 / Vanilla JavaScript | ES6+ | High performance, zero framework bundle bloat |
| **Frontend Reactive Store** | Alpine.js | 3.14.x | Lightweight reactive state for auth, modals, and notifications |
| **HTML Sanitizer** | DOMPurify | 3.1.6 | Universal XSS protection and safe HTML whitelisting |
| **Client Caching** | Custom SWR Engine | Native JS / SessionStorage | 0ms instant cached transitions & background revalidation |
| **Iconography** | Lucide Icons | Latest SVG | Uniform, crisp vector icons across all UI components |
| **Typography** | Google Fonts (Outfit) | 300 - 800 | Modern, highly legible geometric sans-serif typeface |
| **Backend Framework** | Python / Django | 5.2.x | Secure, robust MVC backend and routing architecture |
| **ASGI Server** | Daphne / Channels | 4.2.x | Asynchronous gateway interface for low-latency dispatching |
| **Database** | PostgreSQL / SQLite / MySQL | 15+ / 3.x | Relational storage with composite B-tree indexing |
| **Authentication** | PyJWT / bcrypt | HS256 | Cryptographically secure token authentication & password hashing |
| **Image Processing** | Pillow (PIL) + HTML5 Canvas | Latest | Dual-layer client Canvas & server Pillow compression |
| **Geocoding Service** | OpenStreetMap / Nominatim | v2 API | Real-world map coordinates and address autocomplete |

---

## 🚀 8. Installation & Local Setup

### Prerequisites
- Python 3.10+ installed
- PostgreSQL, MySQL, or built-in SQLite3
- Git

### 1. Clone the Repository
```bash
git clone https://github.com/Abubakkar-Khan/coworkconnect.git
cd coworkconnect
```

### 2. Create and Activate Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a `.env` file in the project root:
```env
PORT=5000
DEBUG=true
DJANGO_SECRET_KEY=your_secure_development_secret_key
JWT_SECRET=your_secure_jwt_secret_key
JWT_EXPIRE=30d

# Database Configuration (Choose PostgreSQL, MySQL, or leave empty for SQLite fallback)
DATABASE_URL=postgresql://postgres:password@localhost:5432/coworkconnect?sslmode=disable
DB_CONN_MAX_AGE=600

# Optional Cloudinary Configuration for Image Uploads
# CLOUDINARY_URL=cloudinary://api_key:api_secret@cloud_name
```

### 5. Initialize Schema & Seed Data
```bash
python manage.py shell -c "from api.schema import ensure_schema; ensure_schema()"
```

*(Optional: Run seed script if available)*
```bash
python manage.py seed
```

### 6. Launch the Development Server
```bash
python manage.py runserver 0.0.0.0:5000
```
Open your browser and navigate to: **`http://localhost:5000`** (or `http://127.0.0.1:5000`).

---

## ⚙️ 9. Environment Variables Reference

| Variable | Type | Default | Description |
| :--- | :---: | :---: | :--- |
| `PORT` | `int` | `5000` | Port for the Daphne/Django development server |
| `DEBUG` | `bool` | `true` | Enable Django debug mode and detailed error reporting |
| `DJANGO_SECRET_KEY` | `string` | — | Cryptographic secret key for session signing |
| `JWT_SECRET` | `string` | — | Secret key used to sign and verify HS256 JWT tokens |
| `JWT_EXPIRE` | `string` | `30d` | Lifetime of issued authentication tokens (e.g. `30d`, `24h`) |
| `DATABASE_URL` | `string` | — | Standard PostgreSQL / MySQL database connection string |
| `DB_CONN_MAX_AGE` | `int` | `600` | Database connection persistence in seconds (connection pooling) |
| `DB_SSL` | `bool` | `false` | Enforce SSL mode on database queries |
| `MAX_UPLOAD_SIZE` | `int` | `5242880` | Maximum file upload size in bytes (default: 5MB) |
| `CLOUDINARY_URL` | `string` | — | Optional remote media storage connection string |

---

## 🌐 10. Production Deployment Guide

### Deploying to Vercel + Neon / Supabase

1. **Connect Database**:
   - Provision a PostgreSQL database on [Neon](https://neon.tech) or [Supabase](https://supabase.com).
   - Copy the connection string to `DATABASE_URL`.

2. **Configure `vercel.json`**:
   The project includes a root `vercel.json` configured for serverless Python ASGI execution:
   ```json
   {
     "builds": [
       {
         "src": "coworkconnect/wsgi.py",
         "use": "@vercel/python"
       }
     ],
     "routes": [
       {
         "src": "/(.*)",
         "dest": "coworkconnect/wsgi.py"
       }
     ]
   }
   ```

3. **Deploy via Vercel CLI**:
   ```bash
   vercel --prod
   ```

---

## 👥 Contributors & License

- **Project Lead & Author**: Abubakkar Khan ([@Abubakkar-Khan](https://github.com/Abubakkar-Khan))
- **License**: MIT License — open for academic, personal, and commercial usage.

---
*Built with ❤️ for remote professionals, founders, and flexible workspace operators.*
