import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from datetime import datetime, timedelta

# Import the app, the get_db dependency to override, and the Base/models for setup
from main import app, get_db
from database import Base
from models import URL, Click

# ---------------------------------------------------------------------------
# Test database setup
# Use an in-memory SQLite database so tests never touch the real url.db file.
# StaticPool forces all connections to reuse the same underlying connection —
# without it, each new session would get a fresh empty in-memory database.
# ---------------------------------------------------------------------------
TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, bind=test_engine)


def override_get_db():
    """Replacement for get_db that uses the in-memory test database."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Tell FastAPI to use the test DB instead of the real one for every request
app.dependency_overrides[get_db] = override_get_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_db():
    """Create all tables before each test and drop them after, ensuring a clean slate."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client():
    """Provides a FastAPI TestClient for making requests in tests."""
    return TestClient(app, raise_server_exceptions=True)


@pytest.fixture
def seeded_url(client):
    """
    Creates a known URL entry via the API and returns the response data.
    Used by tests that need a URL to already exist in the database.
    """
    response = client.post("/url", json={"url": "https://www.example.com"})
    return response.json()


# ---------------------------------------------------------------------------
# GET /all
# ---------------------------------------------------------------------------

def test_get_all_empty(client):
    """GET /all should return an empty list when the database has no entries."""
    response = client.get("/all")
    assert response.status_code == 200
    assert response.json() == []


def test_get_all_returns_entries(client, seeded_url):
    """GET /all should return a list containing all stored URL records."""
    response = client.get("/all")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["short_code"] == seeded_url["short_code"]
    assert data[0]["original_url"] == seeded_url["original_url"]


def test_get_all_returns_multiple_entries(client):
    """GET /all should return all records when multiple URLs have been created."""
    client.post("/url", json={"url": "https://www.example.com"})
    client.post("/url", json={"url": "https://www.google.com"})
    response = client.get("/all")
    assert response.status_code == 200
    assert len(response.json()) == 2


# ---------------------------------------------------------------------------
# POST /url  —  random short code
# ---------------------------------------------------------------------------

def test_create_url_random_code(client):
    """POST /url should create a short URL and return a 6-character short code."""
    response = client.post("/url", json={"url": "https://www.example.com"})
    assert response.status_code == 200
    data = response.json()
    assert "short_code" in data
    assert len(data["short_code"]) == 6
    assert data["original_url"] == "https://www.example.com/"
    assert data["short_code"] in data["short_url"]


def test_create_url_no_expiry(client):
    """POST /url without expires_in_minutes should set expires_at to null."""
    response = client.post("/url", json={"url": "https://www.example.com"})
    assert response.status_code == 200
    assert response.json()["expires_at"] is None


def test_create_url_with_expiry(client):
    """POST /url with expires_in_minutes should return a non-null expires_at timestamp."""
    response = client.post("/url", json={"url": "https://www.example.com", "expires_in_minutes": 60})
    assert response.status_code == 200
    assert response.json()["expires_at"] is not None


def test_create_url_invalid_url(client):
    """POST /url with a non-URL string should return 422 Unprocessable Entity."""
    response = client.post("/url", json={"url": "not-a-valid-url"})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# POST /url  —  custom short code
# ---------------------------------------------------------------------------

def test_create_url_custom_code(client):
    """POST /url with a valid custom_code should use that code as the short code."""
    response = client.post("/url", json={"url": "https://www.example.com", "custom_code": "mycode"})
    assert response.status_code == 200
    assert response.json()["short_code"] == "mycode"


def test_create_url_custom_code_duplicate(client):
    """POST /url with a custom_code that already exists should return 409 Conflict."""
    client.post("/url", json={"url": "https://www.example.com", "custom_code": "mycode"})
    response = client.post("/url", json={"url": "https://www.google.com", "custom_code": "mycode"})
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_create_url_custom_code_too_short(client):
    """POST /url with a custom_code of 3 characters or fewer should return 422."""
    response = client.post("/url", json={"url": "https://www.example.com", "custom_code": "abc"})
    assert response.status_code == 422


def test_create_url_custom_code_too_long(client):
    """POST /url with a custom_code of 15 characters or more should return 422."""
    response = client.post("/url", json={"url": "https://www.example.com", "custom_code": "a" * 15})
    assert response.status_code == 422


def test_create_url_custom_code_non_alphanumeric(client):
    """POST /url with a custom_code containing special characters should return 422."""
    response = client.post("/url", json={"url": "https://www.example.com", "custom_code": "my-code!"})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /short_url/{code}  —  redirect
# ---------------------------------------------------------------------------

def test_redirect_valid_code(client, seeded_url):
    """GET /short_url/{code} with a valid code should redirect (3xx) to the original URL."""
    code = seeded_url["short_code"]
    # allow_redirects=False so we can inspect the redirect response itself
    response = client.get(f"/short_url/{code}", follow_redirects=False)
    assert response.status_code in (301, 302, 307, 308)
    assert "example.com" in response.headers["location"]


def test_redirect_records_click(client, seeded_url):
    """GET /short_url/{code} should record a click entry in the database."""
    code = seeded_url["short_code"]
    client.get(f"/short_url/{code}", follow_redirects=False)
    # Verify the click was recorded by checking the stats endpoint
    stats = client.get(f"/stats/{code}").json()
    assert stats["total_clicks"] == 1


def test_redirect_invalid_code(client):
    """GET /short_url/{code} with a non-existent code should return 404."""
    response = client.get("/short_url/doesnotexist", follow_redirects=False)
    assert response.status_code == 404


def test_redirect_expired_url(client):
    """GET /short_url/{code} for an expired URL should return 410 Gone."""
    # Create a URL that expired 1 minute ago
    response = client.post("/url", json={
        "url": "https://www.example.com",
        "custom_code": "expired",
        "expires_in_minutes": -1  # negative value sets expiry in the past
    })
    assert response.status_code == 200
    response = client.get("/short_url/expired", follow_redirects=False)
    assert response.status_code == 410
    assert "expired" in response.json()["detail"].lower()


def test_redirect_not_expired_url(client):
    """GET /short_url/{code} for a URL with a future expiry should still redirect."""
    client.post("/url", json={
        "url": "https://www.example.com",
        "custom_code": "future",
        "expires_in_minutes": 60
    })
    response = client.get("/short_url/future", follow_redirects=False)
    assert response.status_code in (301, 302, 307, 308)


# ---------------------------------------------------------------------------
# GET /stats/{code}
# ---------------------------------------------------------------------------

def test_stats_valid_code_no_clicks(client, seeded_url):
    """GET /stats/{code} should return 0 total_clicks when the URL has never been visited."""
    code = seeded_url["short_code"]
    response = client.get(f"/stats/{code}")
    assert response.status_code == 200
    data = response.json()
    assert data["short_code"] == code
    assert data["total_clicks"] == 0
    assert data["clicks"] == []
    assert data["original_url"] == seeded_url["original_url"]


def test_stats_click_count_increments(client, seeded_url):
    """GET /stats/{code} total_clicks should increase with each visit to the short URL."""
    code = seeded_url["short_code"]
    client.get(f"/short_url/{code}", follow_redirects=False)
    client.get(f"/short_url/{code}", follow_redirects=False)
    stats = client.get(f"/stats/{code}").json()
    assert stats["total_clicks"] == 2


def test_stats_click_contains_ip_and_agent(client, seeded_url):
    """GET /stats/{code} click entries should include time, ip, and agent fields."""
    code = seeded_url["short_code"]
    client.get(f"/short_url/{code}", follow_redirects=False)
    stats = client.get(f"/stats/{code}").json()
    click = stats["clicks"][0]
    assert "time" in click
    assert "ip" in click
    assert "agent" in click


def test_stats_invalid_code(client):
    """GET /stats/{code} with a non-existent code should return 404."""
    response = client.get("/stats/doesnotexist")
    assert response.status_code == 404
    assert "does not exist" in response.json()["detail"].lower()


def test_stats_shows_expiry(client):
    """GET /stats/{code} should include the expires_at field in the response."""
    client.post("/url", json={
        "url": "https://www.example.com",
        "custom_code": "exptest",
        "expires_in_minutes": 30
    })
    stats = client.get("/stats/exptest").json()
    assert stats["expires_at"] is not None
