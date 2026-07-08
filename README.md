# Pageforge — AI E-Book Generator

An AI-powered SaaS web app for generating fully illustrated ebooks. Describe a topic, pick a style and length, and the app generates a complete illustrated book for you.

---

## What Was Built

### Backend (Python / FastAPI)

A REST API with SQLite persistence.

| File | Purpose |
|---|---|
| `backend/app/main.py` | FastAPI app entry point with CORS and lifespan |
| `backend/app/database.py` | SQLite engine + session factory |
| `backend/app/models/book.py` | `Book` table model with status, type, progress, cover hue |
| `backend/app/schemas/book.py` | Pydantic schemas for create/update |
| `backend/app/routers/books.py` | Full CRUD: list, create, get, update, delete |
| `backend/app/routers/credits.py` | Credits balance + consume endpoint |
| `backend/tests/` | 18 tests covering ordering, validation, partial update, deletion, credits |

**API endpoints:**

```
GET    /api/books/          List all books (newest first)
POST   /api/books/          Create a new book
GET    /api/books/{id}      Get a single book
PATCH  /api/books/{id}      Partial update (favorite, status, progress…)
DELETE /api/books/{id}      Delete a book
GET    /api/credits/        Get remaining credits
POST   /api/credits/consume Decrement credits by 1
```

---

### Frontend (Next.js 15 / TypeScript)

A dark editorial app dashboard — no Tailwind, pure CSS Modules with OKLCH color tokens.

| Component | What it does |
|---|---|
| `Sidebar` | Navigation (All / Favorites / Generating / Types), credits meter with live bar |
| `Topbar` | Search input, grid/list view toggle, sort control, "New Book" button |
| `BookCard` | Portrait 2:3 card with 3D perspective tilt on hover, spine shadow, color-coded by hue, hover overlay with Read/Delete, generating shimmer + progress bar |
| `BookGrid` | Auto-fill responsive grid with staggered entrance animation and shimmer skeletons on load |
| `NewBookDrawer` | Slide-up drawer (iOS easing via `motion/react`) — title, prompt, book type pills, page count slider, illustration style swatches |
| `LibraryClient` | Main page state: filtering by nav, search, create, delete, favorite toggle |

**Design system:**
- OKLCH color tokens throughout (dark editorial palette)
- Geist font via `next/font/google`
- Phosphor Icons — no emoji used as UI icons
- `motion/react` for the drawer animation
- `cubic-bezier(0.23, 1, 0.32, 1)` ease-out on all transitions
- `scale(0.97)` on `:active` for tactile button feedback
- `prefers-reduced-motion` respected everywhere

---

## Project Structure

```
AI E-Book Generator/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── database.py
│   │   ├── models/book.py
│   │   ├── schemas/book.py
│   │   └── routers/
│   │       ├── books.py
│   │       └── credits.py
│   ├── tests/
│   │   ├── conftest.py
│   │   └── test_books.py
│   └── requirements.txt
└── frontend/
    ├── app/
    │   ├── layout.tsx
    │   ├── page.tsx              ← redirects to /library
    │   └── (app)/library/
    │       ├── page.tsx
    │       ├── library-client.tsx
    │       └── library.module.css
    ├── components/
    │   ├── sidebar/
    │   ├── topbar/
    │   ├── book-card/
    │   ├── book-grid/
    │   └── new-book-drawer/
    ├── lib/
    │   ├── api.ts
    │   └── types.ts
    └── styles/globals.css
```

---

## Running the Backend

**Requirements:** Python 3.11+

```bash
# 1. Go to the backend folder
cd backend

# 2. Create a virtual environment (first time only)
python -m venv venv

# 3. Activate it
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# 4. Install dependencies (first time only)
pip install -r requirements.txt

# 5. Start the server
uvicorn app.main:app --reload
```

The API will be live at **http://localhost:8000**

Interactive API docs: **http://localhost:8000/docs**

### Running Backend Tests

```bash
# Make sure the virtual environment is activated, then:
pytest tests/ -v
```

Expected output: **18 passed**

---

## Running the Frontend

**Requirements:** Node.js 18+

```bash
# 1. Go to the frontend folder
cd frontend

# 2. Install dependencies (first time only)
npm install

# 3. Start the dev server
npm run dev
```

The app will be live at **http://localhost:3000** and will automatically redirect to **/library**.

> Make sure the backend is also running, otherwise the book list will be empty and creating books will fail.

### Environment Variable (optional)

By default the frontend talks to `http://localhost:8000/api`. To change this, create a `.env.local` file in the `frontend/` folder:

```
NEXT_PUBLIC_API_URL=http://your-api-host/api
```

### Production Build

```bash
npm run build
npm start
```

---

## Running Everything Together

Open two terminals side by side:

**Terminal 1 — Backend:**
```bash
cd backend
venv\Scripts\activate        # Windows
uvicorn app.main:app --reload
```

**Terminal 2 — Frontend:**
```bash
cd frontend
npm run dev
```

Then open **http://localhost:3000** in your browser.
