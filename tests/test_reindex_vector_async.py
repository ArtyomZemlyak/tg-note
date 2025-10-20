import pytest
from types import SimpleNamespace

# Import the MCP Hub server module where tools are defined
from src.mcp import mcp_hub_server as hub


class StubVectorManager:
    def __init__(self):
        self.reindexed = False

    async def index_knowledge_base(self, force: bool = False):
        self.reindexed = True
        # Minimal realistic stats structure expected by handler
        return {
            "files_processed": 1 if force else 0,
            "files_skipped": 0 if force else 1,
            "chunks_created": 0,
            "errors": [],
            "deleted_files": 0,
        }

    async def search(self, query: str, top_k: int = 5, filter_dict=None):
        # Return predictable fake results
        return [{"text": f"result-{i}", "score": 1.0 - i * 0.1} for i in range(top_k)]


@pytest.mark.asyncio
async def test_reindex_vector_no_nested_loop(monkeypatch):
    # Ensure tool is considered available
    monkeypatch.setattr(hub, "check_vector_search_availability", lambda: True)

    # Provide an async stub manager
    stub_manager = StubVectorManager()

    async def fake_get_manager():
        return stub_manager

    monkeypatch.setattr(hub, "get_vector_search_manager", fake_get_manager)

    # Call async tool inside a running event loop; should not raise nested loop errors
    res = await hub.reindex_vector(force=False, user_id=123)

    assert res["success"] is True
    assert "stats" in res
    assert isinstance(res["stats"], dict)


@pytest.mark.asyncio
async def test_vector_search_no_nested_loop(monkeypatch):
    # Ensure tool is considered available
    monkeypatch.setattr(hub, "check_vector_search_availability", lambda: True)

    # Provide an async stub manager
    stub_manager = StubVectorManager()

    async def fake_get_manager():
        return stub_manager

    monkeypatch.setattr(hub, "get_vector_search_manager", fake_get_manager)

    # Call async tool inside a running event loop; should not raise nested loop errors
    res = await hub.vector_search(query="hello", top_k=3, user_id=1)

    assert res["success"] is True
    assert res["results_count"] == 3
    assert isinstance(res["results"], list)
