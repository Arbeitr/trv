"""
Overpass API Client with 3-tier caching and rate limiting.
Respects 1 request per minute limit on public Overpass API.
"""

import os
import sqlite3
import time
import json
import hashlib
import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "cache", "overpass_cache.db")

# Overpass API settings
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
RATE_LIMIT_SECONDS = 60  # 1 request per minute
CACHE_EXPIRY_SECONDS = 30 * 24 * 60 * 60  # 30 days

# In-memory cache (Layer 1)
_memory_cache = {}

# Rate limiting
_last_request_time = 0

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _get_query_hash(query):
    """Generate a hash for the query to use as cache key."""
    return hashlib.sha256(query.encode('utf-8')).hexdigest()


def _check_memory_cache(query_hash):
    """Check in-memory cache (Layer 1)."""
    if query_hash in _memory_cache:
        logger.debug(f"Cache hit (memory): {query_hash[:8]}")
        return _memory_cache[query_hash]
    return None


def _check_db_cache(query_hash):
    """Check SQLite cache (Layer 2)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT response_data, timestamp 
        FROM overpass_cache 
        WHERE query_hash = ?
    """, (query_hash,))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        response_data, timestamp = row
        current_time = int(time.time())
        
        # Check if cache is still valid
        if (current_time - timestamp) < CACHE_EXPIRY_SECONDS:
            logger.debug(f"Cache hit (database): {query_hash[:8]}")
            data = json.loads(response_data)
            # Store in memory cache for faster access
            _memory_cache[query_hash] = data
            return data
        else:
            logger.debug(f"Cache expired: {query_hash[:8]}")
    
    return None


def _store_in_cache(query_hash, query_text, response_data):
    """Store response in both memory and database cache."""
    # Store in memory (Layer 1)
    _memory_cache[query_hash] = response_data
    
    # Store in database (Layer 2)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    current_time = int(time.time())
    response_json = json.dumps(response_data)
    
    cursor.execute("""
        INSERT OR REPLACE INTO overpass_cache (query_hash, query_text, response_data, timestamp)
        VALUES (?, ?, ?, ?)
    """, (query_hash, query_text, response_json, current_time))
    
    conn.commit()
    conn.close()
    
    logger.debug(f"Cached response: {query_hash[:8]}")


def _wait_for_rate_limit():
    """Wait if necessary to respect rate limit."""
    global _last_request_time
    
    current_time = time.time()
    time_since_last_request = current_time - _last_request_time
    
    if time_since_last_request < RATE_LIMIT_SECONDS:
        wait_time = RATE_LIMIT_SECONDS - time_since_last_request
        logger.info(f"Rate limit: waiting {wait_time:.1f}s before next request...")
        time.sleep(wait_time)
    
    _last_request_time = time.time()


def _create_session():
    """Create a requests session with retry logic."""
    session = requests.Session()
    
    retry_strategy = Retry(
        total=3,
        backoff_factor=2,  # 2, 4, 8 seconds
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"]
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session


def query_overpass(query, cache=True):
    """
    Query Overpass API with 3-tier caching and rate limiting.
    
    Args:
        query: Overpass QL query string
        cache: Whether to use caching (default True)
    
    Returns:
        JSON response from Overpass API
    """
    query_hash = _get_query_hash(query)
    
    # Check caches if caching is enabled
    if cache:
        # Layer 1: Memory cache
        cached_response = _check_memory_cache(query_hash)
        if cached_response:
            return cached_response
        
        # Layer 2: Database cache
        cached_response = _check_db_cache(query_hash)
        if cached_response:
            return cached_response
    
    # No cache hit, need to make actual request
    logger.info(f"Querying Overpass API... (hash: {query_hash[:8]})")
    
    # Respect rate limit
    _wait_for_rate_limit()
    
    try:
        session = _create_session()
        
        response = session.post(
            OVERPASS_URL,
            data={"data": query},
            timeout=180,  # 3 minutes timeout
            headers={"User-Agent": "TrainRouteVisualizer/1.0"}
        )
        
        # Check for rate limit headers
        if response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', 60))
            logger.warning(f"Rate limited by server. Waiting {retry_after}s...")
            time.sleep(retry_after)
            # Retry once
            response = session.post(
                OVERPASS_URL,
                data={"data": query},
                timeout=180,
                headers={"User-Agent": "TrainRouteVisualizer/1.0"}
            )
        
        response.raise_for_status()
        data = response.json()
        
        # Store in cache
        if cache:
            _store_in_cache(query_hash, query, data)
        
        logger.info(f"✓ Query successful: {len(data.get('elements', []))} elements")
        return data
        
    except requests.exceptions.Timeout:
        logger.error("Request timed out")
        raise Exception("Overpass API request timed out")
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        raise Exception(f"Overpass API request failed: {e}")
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response: {e}")
        raise Exception("Invalid JSON response from Overpass API")


def clear_cache():
    """Clear all caches."""
    global _memory_cache
    _memory_cache = {}
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM overpass_cache")
    conn.commit()
    conn.close()
    
    logger.info("Cache cleared")
