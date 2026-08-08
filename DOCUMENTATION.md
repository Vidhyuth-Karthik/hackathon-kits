# Hackathon Starter Kit — Code Walkthrough

This document explains what every file does and how a request travels
through the system, from clicking "Log In" in the browser to reading
a row back out of SQLite. It's written for someone who is comfortable
with basic Python but new to FastAPI and web apps in general.

## 1. The big picture

```
Browser (client/)  --HTTP-->  FastAPI (api/)  --SQL-->  SQLite (data/app.db)
```

One process — `uvicorn` running `api/main.py` — does two jobs at once:

1. It serves the plain HTML/CSS/JS files in `client/` whenever the
   browser asks for a page (like `/index.html`).
2. It handles API calls under `/api/...` (like `/api/auth/login`).

Because both the frontend and the API are served from the exact same
origin (`http://127.0.0.1:8000`), the browser never has to make a
cross-origin request. That's why there's no CORS configuration
anywhere in this project — it simply isn't needed.

## 2. Folder layout

```
hackathon-starter-kit/
├── api/
│   ├── main.py            entry point — creates the app, wires everything together
│   ├── database.py        opens SQLite connections, creates tables
│   ├── security.py        password hashing (no external crypto library needed)
│   ├── requirements.txt   the two pip packages this project needs
│   └── routers/
│       ├── auth.py        signup / login / logout / "who am I" endpoints
│       └── ai.py          placeholder for future AI endpoints
├── client/
│   ├── index.html         login + signup page
│   ├── home.html          page shown after a successful login
│   ├── style.css          shared styling for both pages
│   └── script.js          shared browser logic for both pages
└── data/
    └── app.db             SQLite database file (created automatically the first time you run the server)
```

## 3. File-by-file

### `api/main.py` — the entry point

This is the file `uvicorn` loads when you run `uvicorn main:app`. It:

1. Creates the `FastAPI()` app object.
2. Registers an **startup event** that calls `init_db()`, so the
   `users` and `sessions` tables exist before any request can hit
   them.
3. **Includes the routers** — `auth.router` and `ai.router` — which
   is what actually adds endpoints like `/api/auth/login` to the app.
   Adding a new feature area later is as simple as writing a new
   router file and adding one more `app.include_router(...)` line
   here.
4. **Mounts the `client/` folder as static files** at `/`, with
   `html=True` so that visiting `/` automatically serves
   `index.html`.

Order matters here: the routers are included *before* the static
mount. FastAPI checks routes in the order they were registered, so an
exact API match like `POST /api/auth/login` is always found before
the catch-all static file handler gets a chance to look at it.

### `api/database.py` — talking to SQLite

Uses Python's built-in `sqlite3` module — nothing to install.

- `DB_PATH` points at `data/app.db`, computed relative to this file
  so it works no matter where you launch the server from.
- `get_connection()` opens a **new** connection every time it's
  called, and sets `row_factory = sqlite3.Row` so query results can
  be read like `row["user_id"]` instead of `row[0]`. Opening a fresh
  connection per request is slightly less "efficient" than reusing
  one, but it completely sidesteps SQLite's threading quirks — a
  reasonable trade for a learning project.
- `init_db()` runs two `CREATE TABLE IF NOT EXISTS` statements:
  - **`users`**: `user_id` (primary key), `password_hash`,
    `password_salt`, `created_at`.
  - **`sessions`**: `token` (primary key), `user_id`, `created_at`.
    This is how the server remembers "this browser is logged in as
    this user" between requests.

### `api/security.py` — password hashing

Passwords are **never** stored in plain text. This file has two
functions built entirely from `hashlib` (also built into Python):

- `hash_password(password, salt=None)` — if no salt is given (i.e.
  during signup), it generates a random 16-byte salt with
  `os.urandom`, then runs the password through
  `hashlib.pbkdf2_hmac("sha256", ...)` 100,000 times. Returns
  `(hash, salt)`.
- `verify_password(password, salt, expected_hash)` — re-hashes the
  attempted password with the *stored* salt and checks whether it
  matches the *stored* hash. Used during login.

The "salt" is just random bytes mixed into the hash so that two users
with the same password don't end up with the same hash in the
database, and so precomputed "rainbow table" attacks don't work.

### `api/routers/auth.py` — the authentication endpoints

This file defines an `APIRouter` with the prefix `/api/auth`, so
every route declared here is automatically namespaced (e.g.
`@router.post("/login")` becomes `/api/auth/login`).

| Endpoint | Method | What it does |
|---|---|---|
| `/api/auth/signup` | POST | Checks the user ID isn't taken, hashes the password, inserts a new row into `users`. |
| `/api/auth/login` | POST | Looks up the user, verifies the password, creates a random session token, stores it in `sessions`, and sends it back as an **httpOnly cookie**. |
| `/api/auth/logout` | POST | Deletes the session row matching the cookie's token, then tells the browser to delete the cookie. |
| `/api/auth/me` | GET | Reads the cookie, looks up the session, and returns the logged-in `user_id` — or `401` if there isn't one. |

The `Credentials` class (a Pydantic `BaseModel`) describes the shape
of the JSON body signup/login expect: `{"user_id": ..., "password":
...}`. FastAPI uses this to automatically validate incoming requests
and reject malformed ones with a clear error, before your function
body even runs.

**Why a cookie instead of returning a token in the JSON response?**
Because the cookie is marked `httponly=True`, JavaScript in the
browser can never read it — only the browser itself can, and it
sends it back automatically on every request to the same site. That
removes an entire class of token-theft bugs a beginner could
otherwise introduce by accidentally logging a token or storing it
somewhere insecure.

The last function, `get_current_user(session_token)`, isn't an
endpoint — it's a shared helper. It takes whatever token was in the
cookie and returns the matching `user_id`, or `None`. This is the
function `routers/ai.py` (and any future protected router) imports to
check "is this request logged in?"

### `api/routers/ai.py` — where AI features will live

Currently contains one example endpoint, `GET /api/ai/ping`, that
does nothing but prove the pattern: it reads the session cookie,
calls `get_current_user()` from `auth.py`, and returns `401` if
nobody's logged in.

This file exists specifically so that adding real AI functionality
later doesn't mean touching `auth.py` or `main.py`. The recipe is:

1. Add a new function to this file (or a new file in `routers/`)
   decorated with `@router.post("/your-endpoint")`.
2. Read the session cookie the same way `ping()` does and call
   `get_current_user()` to enforce login.
3. If you add a new file instead of editing this one, register it in
   `main.py` with one more `app.include_router(...)` line.

### `client/index.html` — login and signup page

A single page with two forms (`#login-form`, `#signup-form`) toggled
by tab buttons. Both forms just collect a user ID and password —
none of the actual request logic lives in this file, it's all in
`script.js`.

### `client/home.html` — the "logged in" page

Shown after a successful login. It has a placeholder
(`#user-id-display`) for the logged-in user's ID and a logout button.
Like `index.html`, it has no logic of its own — `script.js` fills in
the blanks.

### `client/style.css` — shared styling

Plain CSS, no framework. Styles the centered card, the tab buttons,
form inputs, and the success/error message text. Shared by both
HTML pages via `<link rel="stylesheet" href="style.css">`.

### `client/script.js` — all the browser-side logic

Both `index.html` and `home.html` load this same file. Each section
checks whether the elements it needs actually exist on the current
page before doing anything, so one file safely serves both pages:

- **`postJSON(url, data)`** — a small wrapper around `fetch()` that
  sends JSON, includes cookies (`credentials: "same-origin"`), and
  throws a JavaScript error with the server's message if the request
  failed.
- **Login/signup section** (only runs if `#login-form` exists): wires
  up the tab-switching buttons, and submits each form's data to
  `/api/auth/login` or `/api/auth/signup`. On successful login, it
  redirects to `/home.html`.
- **Home page section** (only runs if `#user-id-display` exists): on
  page load, calls `/api/auth/me` to check whether the visitor is
  actually logged in. If not, it redirects back to `/index.html`. The
  logout button calls `/api/auth/logout` and redirects back to the
  login page.

## 4. Full request sequence: signing up, logging in, and visiting the home page

Here's what happens, step by step, for a brand-new user:

```
1. Browser requests  GET /
   → main.py's static mount serves client/index.html (html=True finds it automatically)

2. User fills in the "Sign Up" form and submits
   → script.js POSTs JSON to /api/auth/signup
   → routers/auth.py: signup()
       - checks the user_id isn't already in the `users` table
       - security.py: hash_password() salts + hashes the password
       - INSERTs a new row into `users`
   → responds 200 {"message": "Account created..."}
   → script.js shows the success message and switches to the Login tab

3. User fills in the "Log In" form and submits
   → script.js POSTs JSON to /api/auth/login
   → routers/auth.py: login()
       - SELECTs the stored hash + salt for that user_id
       - security.py: verify_password() re-hashes the attempt and compares
       - if it matches: generates a random token (secrets.token_hex),
         INSERTs it into `sessions`, and calls response.set_cookie(...)
   → the HTTP response includes  Set-Cookie: session_token=<random>; HttpOnly
   → script.js redirects the browser to /home.html

4. Browser requests  GET /home.html
   → the browser automatically attaches the session_token cookie
     (this happens for every request from now on — script.js never
     has to touch the token directly)
   → main.py's static mount serves client/home.html

5. home.html loads script.js, which immediately calls GET /api/auth/me
   → the cookie is sent automatically
   → routers/auth.py: me() → get_current_user(session_token)
       - SELECTs `sessions` for a row matching that token
       - returns the associated user_id
   → responds 200 {"user_id": "..."}
   → script.js fills in #user-id-display with the returned name

6. User clicks "Log Out"
   → script.js POSTs to /api/auth/logout (cookie sent automatically)
   → routers/auth.py: logout()
       - DELETEs the matching row from `sessions`
       - response.delete_cookie(...) tells the browser to drop the cookie
   → script.js redirects back to /index.html
```

If a logged-out visitor (no valid cookie) tries to open `/home.html`
directly, step 5 still runs — `/api/auth/me` will respond `401`
because there's no matching session — and `script.js` immediately
redirects them to `/index.html` instead of showing the page.

## 5. Where a protected AI endpoint fits in

Once you add a real endpoint to `routers/ai.py` (following the
`ping()` example), the sequence looks the same as steps 4–5 above:
the browser's cookie is sent automatically, the endpoint calls
`get_current_user()` from `auth.py`, and it either proceeds (user is
logged in) or returns `401` (user is not). The frontend would call it
with `fetch("/api/ai/your-endpoint", { credentials: "same-origin" })`
the same way `script.js` already calls `/api/auth/me`.

## 6. Troubleshooting tips for beginners

- **"Address already in use" when starting uvicorn** — a previous
  server is still running. Find it with `lsof -i :8000` and stop it,
  or start this one on a different port with `--port 8001`.
- **Changes to `client/*.html`, `.css`, or `.js` don't show up** —
  hard-refresh the browser (the static files aren't cached by the
  server, but your browser might cache them).
- **Changes to `.py` files don't show up** — make sure you started
  uvicorn with `--reload`, or restart it manually.
- **Want to start over with a clean database** — stop the server and
  delete `data/app.db`; it will be recreated (empty) the next time
  the server starts.
- **"Not logged in" right after logging in** — check your browser
  isn't blocking third-party or all cookies for `127.0.0.1`; try
  `localhost` instead, or check DevTools → Application → Cookies.
