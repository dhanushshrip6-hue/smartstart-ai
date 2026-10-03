"""DEV/TEST ONLY: runs the real Flask app with the HTTP layer faked (synthetic data), for browser smoke tests offline."""
import json, os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))
os.environ["DATABASE_PATH"] = os.path.join(tempfile.mkdtemp(), "mock.db")
os.environ["GEMINI_API_KEY"] = "mock"
os.environ["RATE_LIMIT_PER_MINUTE"] = "200"
import osm, gemini  # noqa: E402
from test_api import FakeResp, overpass_answer  # noqa: E402

osm.requests.get = lambda url, **kw: FakeResp([{"lat": "13.0827", "lon": "80.2707", "display_name": "Chennai, Tamil Nadu, India", "address": {"city": "Chennai", "state": "Tamil Nadu"}, "osm_type": "relation", "osm_id": 1}])
def post(url, **kw):
    if "generativelanguage" in url:
        return FakeResp({"candidates": [{"content": {"parts": [{"text": json.dumps({k: f"Mock paragraph for {k}.\n\nSecond mock paragraph." for k in gemini.SECTIONS})}]}}]})
    return FakeResp(overpass_answer(kw["data"]["data"]))
osm.requests.post = post
gemini.requests.post = post
osm.time.sleep = lambda s: None
import app  # noqa: E402
app.app.run(port=5055)
