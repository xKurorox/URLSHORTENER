# URL Shortener API

A REST API built with FastAPI that shortens URLs, tracks clicks, and supports custom codes and expiration dates.

## Features

- Shorten any URL and receive a unique short code
- Custom short codes — choose your own alias (alphanumeric, 4–14 characters)
- Click tracking — logs IP address, user agent, and timestamp for every visit
- Analytics endpoint — view total clicks and detailed click history
- URL expiration — set a time limit in minutes on any shortened link
- URL validation — only accepts valid HTTP/HTTPS URLs
- Input validation — enforces alphanumeric codes within length limits
- Proper HTTP status codes — 301 redirects, 404 not found, 409 conflicts, 410 gone, 422 validation error

## Setup

```bash
# Clone the repository
git clone https://github.com/xKurorox/url-shortener.git
cd url-shortener

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn main:app --reload
```

The API will be available at `http://127.0.0.1:8000`. Interactive docs are at `http://127.0.0.1:8000/docs`.

## API Endpoints

### POST /url — Shorten a URL

Creates a shortened URL. Custom codes and expiration are optional.

**Request body:**

```json
{
  "url": "https://www.example.com/some/long/path",
  "custom_code": "mylink",
  "expires_in_minutes": 60
}
```

Only `url` is required. `custom_code` and `expires_in_minutes` are optional.

**Response:**

```json
{
  "short_code": "mylink",
  "short_url": "http://127.0.0.1:8000/short_url/mylink",
  "original_url": "https://www.example.com/some/long/path",
  "expires_at": "2026-03-18T04:58:56.972666"
}
```

**Error responses:**

- `409` — Custom code already taken
- `422` — Invalid URL or custom code fails validation

### GET /short_url/{code} — Redirect

Visiting a short URL redirects to the original. Each visit is logged for analytics.

**Error responses:**

- `404` — Short code not found
- `410` — Link has expired

### GET /stats/{code} — View Analytics

Returns click statistics for a shortened URL.

**Response:**

```json
{
  "short_code": "mylink",
  "original_url": "https://www.example.com/some/long/path",
  "total_clicks": 3,
  "clicks": [
    {
      "time": "2026-03-17T10:30:00",
      "ip": "127.0.0.1",
      "agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)..."
    }
  ],
  "expires_at": "2026-03-18T04:58:56.972666"
}
```

## Project Structure

```
url-shortener/
├── main.py            # API endpoints and application logic
├── database.py        # Database connection and session setup
├── models.py          # SQLAlchemy models (URL and Click tables)
├── requirements.txt   # Python dependencies
├── .gitignore         # Files excluded from version control
└── README.md
```

## Database Schema

### urls

| Column       | Type     | Description                    |
|-------------|----------|--------------------------------|
| id          | Integer  | Primary key                    |
| short_code  | String   | Unique short code              |
| original_url| String   | The original long URL          |
| created_at  | DateTime | When the link was created      |
| expires_at  | DateTime | When the link expires (optional)|

### clicks

| Column      | Type     | Description                          |
|------------|----------|--------------------------------------|
| id         | Integer  | Primary key                          |
| url_id     | Integer  | Foreign key referencing urls table    |
| click_date | DateTime | When the click happened              |
| ip_address | String   | Visitor's IP address                 |
| user_agent | String   | Visitor's browser/device info        |

## Tech Stack

- **Python** — core language
- **FastAPI** — web framework
- **SQLAlchemy** — ORM for database interaction
- **SQLite** — database (easily swappable to PostgreSQL)
- **Pydantic** — request/URL validation
- **Uvicorn** — ASGI server

## Future Improvements

- Rate limiting to prevent abuse
- Migrate to PostgreSQL for production use
- Add a frontend interface
- Dockerize for easy deployment
- Deploy to a cloud provider