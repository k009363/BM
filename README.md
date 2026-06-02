# Blog Media Platform — V7

A modern, full-stack social blogging platform built with React + Flask, backed by MongoDB and Cloudinary, deployed on Render.

---

## Features

### Landing & Auth
- **Public Landing Page** — App overview, feature highlights, live user stats, and sign-up CTA visible before login
- **JWT Authentication** — Secure register/login with auto token refresh
- **Admin Role** — Set via `ADMIN_EMAIL` env var on register, or promote existing users via the `/api/auth/promote-admin` endpoint

### Blogging
- **Rich Text Editor** — Full WYSIWYG editing with React Quill (images, headings, code blocks, quotes)
- **Public & Private Posts** — Control visibility per post (public = everyone, private = followers only)
- **Cover Images** — Stored on Cloudinary, served via CDN
- **Blog Feed** — Paginated, tag-filtered, sorted by latest
- **Interactions** — Like, comment, and share on any blog post

### Wishes ✨ *(new in V7)*
- **Creative Wish Cards** — 10 template presets (Birthday, Anniversary, New Year, Congrats, Get Well, etc.)
- **Rich Customisation** — Custom icon (72 emojis / 6 categories), 4 font families, 4 font sizes, bold/italic, text alignment, 6 background patterns, 12 color presets, custom color pickers, 6 border/frame styles
- **Time Duration** — Set wish visibility: 1 hour / 6 hours / 1 day / 3 days / 1 week / 1 month / Forever
- **Public & Private** — Public wishes appear in the feed; private only visible to users you share with
- **Share to User** — Send a wish directly to another user with in-app + push notification
- **Share to Platform** — WhatsApp, Twitter/X, Facebook, Copy Link, Native Share API
- **Download as Image** — Canvas-generated PNG export of the wish card
- **Share Status** — See which users you've shared a wish with
- **Search & Filter** — Filter by template, visibility, expiry status; search by title/message/author

### Social
- **User Profiles** — Avatar, bio, followers/following counts
- **Follow System** — Send, accept, reject follow requests; unfollow; view follower/following lists
- **Real-time Chat** — 1-on-1 and group chats via Socket.IO with typing indicators and read receipts
- **In-app Notifications** — Likes, comments, shares, follows, wishes — with read/unread filter and mark-all-read

### Push Notifications *(new in V7)*
Web Push (VAPID) browser notifications — works even when the browser is closed:

| Event | Who receives it |
|---|---|
| Follow request sent | Target user |
| Follow request accepted | Requester |
| Blog liked | Blog author |
| Blog commented | Blog author |
| Blog shared | Blog author |
| New blog published | All followers (up to 50) |
| New message (offline) | Receiver |
| Wish shared | Recipient user |

### Admin Dashboard
- User management (activate / deactivate)
- Blog management (view all, delete)
- Platform stats (users, blogs, comments, messages)
- **Site Settings** — Update footer "Powered By" text and year from the dashboard

---

## Technology Stack

**Frontend**
| | |
|---|---|
| React 18 (Vite) | UI framework |
| React Router DOM | Client-side routing |
| Axios | HTTP requests |
| Socket.IO Client | Real-time WebSocket events |
| React Quill | WYSIWYG blog editor |
| HTML5 Canvas API | Wish card image export |
| Web Push API | Browser push notification subscription |
| Vanilla CSS | Custom responsive styling |

**Backend**
| | |
|---|---|
| Python / Flask | API server |
| Flask-JWT-Extended | JWT authentication |
| Flask-SocketIO | WebSocket (chat + notifications) |
| PyMongo | MongoDB driver |
| Cloudinary SDK | Image upload & CDN |
| pywebpush | Web Push (VAPID) notification delivery |
| bcrypt | Password hashing |

**Infrastructure**
| | |
|---|---|
| MongoDB Atlas | Database (all collections) |
| Cloudinary | Image storage & CDN |
| Render (free plan) | Backend hosting |

---

## Environment Variables

Create `backend/.env` with:

```env
FLASK_APP=run.py
FLASK_ENV=development
SECRET_KEY=your_flask_secret
JWT_SECRET_KEY=your_jwt_secret
CLIENT_URL=http://localhost:5173
PORT=5000

# Admin
ADMIN_EMAIL=your_admin@email.com
ADMIN_SETUP_KEY=a_random_secret_to_promote_existing_users

# MongoDB
MONGO_URI=mongodb+srv://<user>:<password>@<cluster>.mongodb.net/
MONGO_DB_NAME=blog_media_db

# Cloudinary
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret

# Web Push (VAPID) — generate once with: python generate_vapid.py
VAPID_PRIVATE_KEY=your_vapid_private_key
VAPID_PUBLIC_KEY=your_vapid_public_key
VAPID_EMAIL=admin@yourdomain.com
```

> **Generate VAPID keys once:**
> ```bash
> cd backend
> python generate_vapid.py
> ```
> Copy the output into `.env` and Render's environment dashboard. Never regenerate after going live — all browser subscriptions would be invalidated.

---

## Run Locally

### 1. Backend

```bash
cd backend

# Create and activate virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate        # macOS/Linux
venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt

# Start the server
python run.py
```

Backend runs at `http://localhost:5000`.

### 2. Frontend

```bash
cd frontend

npm install
npm start
```

Frontend runs at `http://localhost:3000`.

> **Note:** Web Push notifications require HTTPS and will not work on `http://localhost`. Test push notifications on your Render deployment.

### 3. Seed the database (optional)

```bash
cd backend
python seed.py           # seed if empty
python seed.py --reset   # clear all data and reseed
```

---

## Project Structure

```
Blog_Media V7/
├── backend/
│   ├── app/
│   │   ├── database/
│   │   │   └── mongo_db.py          # MongoDB collections & wrapper
│   │   ├── middleware/
│   │   │   └── auth.py              # JWT + admin guards
│   │   ├── routes/
│   │   │   ├── auth.py              # Register, login, profile
│   │   │   ├── blogs.py             # Blog CRUD
│   │   │   ├── interactions.py      # Likes, comments, shares
│   │   │   ├── follow.py            # Follow system
│   │   │   ├── chat.py              # 1-on-1 & group chat REST
│   │   │   ├── notifications.py     # In-app notifications
│   │   │   ├── users.py             # User search & profile
│   │   │   ├── admin.py             # Admin endpoints
│   │   │   ├── wishes.py            # Wishes feature
│   │   │   ├── push.py              # Push subscription management
│   │   │   ├── config.py            # Site config (footer)
│   │   │   └── stats.py             # Public stats
│   │   ├── sockets/
│   │   │   └── socket_events.py     # Socket.IO chat & notification events
│   │   └── utils/
│   │       ├── helpers.py           # Cloudinary upload helper
│   │       └── push_helper.py       # Web Push (VAPID) sender
│   ├── db_seed/                     # JSON files for Atlas import
│   ├── generate_vapid.py            # One-time VAPID key generator
│   ├── seed.py                      # Database seed script
│   ├── requirements.txt
│   └── run.py
│
└── frontend/
    ├── public/
    │   ├── sw.js                    # Service Worker (push notifications)
    │   └── _redirects               # Render/Netlify SPA routing fix
    └── src/
        ├── components/
        │   ├── Navbar.jsx
        │   ├── BlogCard.jsx
        │   ├── CommentSection.jsx
        │   ├── FollowButton.jsx
        │   ├── LoadingSpinner.jsx
        │   └── RichEditor.jsx
        ├── context/
        │   ├── AuthContext.jsx       # Auth state + push subscribe/unsubscribe
        │   └── SocketContext.jsx     # Socket.IO connection
        ├── pages/
        │   ├── LandingPage.jsx       # Public landing page
        │   ├── Home.jsx              # Authenticated feed
        │   ├── Login.jsx
        │   ├── Register.jsx
        │   ├── BlogDetail.jsx
        │   ├── CreateBlog.jsx
        │   ├── EditBlog.jsx
        │   ├── Profile.jsx
        │   ├── Chat.jsx
        │   ├── Notifications.jsx
        │   ├── Wishes.jsx            # Wishes feed + search/filter
        │   ├── CreateWish.jsx        # Wish editor with rich styling
        │   └── AdminDashboard.jsx
        ├── utils/
        │   ├── api.js                # Axios instance
        │   ├── push.js               # Push subscribe/unsubscribe
        │   └── wishTemplates.js      # Templates, fonts, colors, canvas export
        └── styles/
            └── index.css
```

---

## Deployment (Render)

1. Push backend to Render as a **Web Service** (Python)
2. Set all environment variables in Render dashboard
3. Deploy frontend as a **Static Site** — the `public/_redirects` file handles SPA routing (fixes 404 on page refresh)
4. Set `CLIENT_URL` in backend env to your frontend's Render URL
