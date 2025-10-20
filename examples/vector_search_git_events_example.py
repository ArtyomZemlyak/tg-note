"""
Example: Vector Search with Git Events

This example demonstrates how git commit events trigger automatic reindexing.
Works for ALL types of agents, including Qwen CLI with internal tools.

AICODE-NOTE: This solves the problem of agents (like Qwen CLI) that use
their own internal tools - we don't see individual file operations,
but we catch the git commit which triggers reindexing.
"""

import asyncio
from pathlib import Path

from loguru import logger

# Event system
from src.core.events import EventType, get_event_bus

# Git operations with events
from src.knowledge_base.git_ops_with_events import GitOpsWithEvents, create_git_ops_for_user

# Vector search manager (would be initialized by bot)
# from src.bot.vector_search_manager import initialize_vector_search_for_bot


def demo_event_listener():
    """
    Demo: Listen to git events
    
    This shows how the event system works.
    In production, BotVectorSearchManager subscribes to these events.
    """

    def on_git_commit(event):
        """Handler for git commit events"""
        logger.info(f"🎯 Git commit detected!")
        logger.info(f"   Message: {event.data.get('commit_message')}")
        logger.info(f"   Repo: {event.data.get('repo_path')}")
        logger.info(f"   User: {event.data.get('user_id')}")
        logger.info(f"   → This would trigger vector search reindexing!")

    def on_git_push(event):
        """Handler for git push events"""
        logger.info(f"📤 Git push detected!")
        logger.info(f"   Remote: {event.data.get('remote')}")
        logger.info(f"   Branch: {event.data.get('branch')}")

    # Subscribe to events
    event_bus = get_event_bus()
    event_bus.subscribe(EventType.KB_GIT_COMMIT, on_git_commit)
    event_bus.subscribe(EventType.KB_GIT_PUSH, on_git_push)

    logger.info("✓ Subscribed to git events")


def demo_autonomous_agent_workflow():
    """
    Demo: Autonomous Agent (uses tool-based file operations)
    
    This agent publishes events for each file operation AND git commit.
    """
    logger.info("\n" + "=" * 60)
    logger.info("DEMO 1: Autonomous Agent Workflow")
    logger.info("=" * 60)

    # This would normally be the agent's KB path
    repo_path = Path("./test_kb")

    # Create GitOps with events
    git_ops = create_git_ops_for_user(repo_path=repo_path, user_id=123, with_events=True)

    logger.info("\n📝 Agent creates/edits files using tools...")
    logger.info("   file_create('note.md') → KB_FILE_CREATED event")
    logger.info("   file_edit('note.md')   → KB_FILE_MODIFIED event")
    logger.info("   (Events trigger reindexing immediately)")

    logger.info("\n💾 Agent commits changes...")
    # This would actually do the commit if repo exists
    # git_ops.commit("Agent completed task")
    logger.info("   git_ops.commit('Done') → KB_GIT_COMMIT event")
    logger.info("   (Another reindex trigger - batched with file events)")

    logger.info("\n✅ Result: Reindexing triggered TWICE")
    logger.info("   1. From file operations (immediate)")
    logger.info("   2. From git commit (backup trigger)")


def demo_qwen_cli_workflow():
    """
    Demo: Qwen CLI Agent (uses internal tools)
    
    This agent ONLY publishes git commit event (we don't see file operations).
    But that's enough!
    """
    logger.info("\n" + "=" * 60)
    logger.info("DEMO 2: Qwen CLI Agent Workflow")
    logger.info("=" * 60)

    # This would normally be the agent's KB path
    repo_path = Path("./test_kb")

    # Create GitOps with events for Qwen CLI
    git_ops = GitOpsWithEvents(repo_path=repo_path, user_id=456)

    logger.info("\n🤖 Qwen CLI agent works with KB...")
    logger.info("   - Uses internal tools (qwen-cli specific)")
    logger.info("   - Creates/modifies files internally")
    logger.info("   ❌ We DON'T see these operations!")
    logger.info("   ❌ No file events published!")

    logger.info("\n💾 Agent finishes and commits...")
    # This would actually do the auto commit if repo exists
    # success, msg = git_ops.auto_commit_and_push("Qwen CLI completed task")
    logger.info("   git_ops.auto_commit_and_push('Done')")
    logger.info("   → KB_GIT_COMMIT event published!")
    logger.info("   → KB_GIT_PUSH event published!")

    logger.info("\n✅ Result: Reindexing triggered from git commit")
    logger.info("   Even though we didn't see individual file changes!")
    logger.info("   Commit = stable point where all changes are finalized")


def demo_comparison():
    """
    Demo: Comparison of different approaches
    """
    logger.info("\n" + "=" * 60)
    logger.info("COMPARISON: Event Sources")
    logger.info("=" * 60)

    logger.info("\n📊 Autonomous Agent (tool-based):")
    logger.info("   Events: file_create, file_edit, file_delete, git_commit")
    logger.info("   Reindex triggers: Multiple (from each operation)")
    logger.info("   Latency: Very low (~2 sec from file change)")

    logger.info("\n📊 Qwen CLI Agent (internal tools):")
    logger.info("   Events: git_commit only")
    logger.info("   Reindex triggers: One (from final commit)")
    logger.info("   Latency: Low (~2 sec from commit)")

    logger.info("\n📊 Old approach (periodic monitoring):")
    logger.info("   Events: None")
    logger.info("   Reindex triggers: Periodic (every 5 min)")
    logger.info("   Latency: High (0-300 sec)")

    logger.info("\n✅ All approaches now work perfectly!")


def demo_multiple_commits():
    """
    Demo: Multiple commits in short time (batching)
    """
    logger.info("\n" + "=" * 60)
    logger.info("DEMO 3: Multiple Commits (Batching)")
    logger.info("=" * 60)

    repo_path = Path("./test_kb")
    git_ops = create_git_ops_for_user(repo_path=repo_path, user_id=789, with_events=True)

    logger.info("\n🔄 Agent makes multiple commits:")

    for i in range(1, 4):
        logger.info(f"\n   Commit {i}/3:")
        # git_ops.commit(f"Update {i}")
        logger.info(f"   git_ops.commit('Update {i}') → KB_GIT_COMMIT event")
        logger.info(f"   → Reindex marked as pending")

    logger.info("\n⏱️  Wait 2 seconds (batching window)...")
    logger.info("\n✅ ONE reindex executed for all 3 commits!")
    logger.info("   More efficient than reindexing 3 times")


async def demo_with_actual_events():
    """
    Demo: Actually run with events
    
    This would work if you have a real KB repo.
    """
    logger.info("\n" + "=" * 60)
    logger.info("DEMO 4: Actual Event Publishing")
    logger.info("=" * 60)

    # Setup event listener
    demo_event_listener()

    # You would need a real git repo for this to work
    logger.info(
        "\n⚠️  This demo requires a real git repository."
        "\n   Set repo_path to your actual KB path to see events."
    )

    # Example with actual events (if repo exists):
    # repo_path = Path("./knowledge_base/user_1")
    # git_ops = create_git_ops_for_user(
    #     repo_path=repo_path,
    #     user_id=1,
    #     with_events=True
    # )
    #
    # # Make a change
    # test_file = repo_path / "test.md"
    # test_file.write_text("# Test\n\nUpdated content")
    #
    # # Commit (will publish event)
    # git_ops.add("test.md")
    # git_ops.commit("Test commit from example")
    #
    # # Wait a bit to see event handling
    # await asyncio.sleep(0.1)


def main():
    """Run all demos"""
    logger.info("🚀 Vector Search Git Events Example")
    logger.info("=" * 60)

    # Demo 1: Autonomous Agent
    demo_autonomous_agent_workflow()

    # Demo 2: Qwen CLI
    demo_qwen_cli_workflow()

    # Demo 3: Comparison
    demo_comparison()

    # Demo 4: Multiple commits
    demo_multiple_commits()

    # Demo 5: Actual events (requires real repo)
    # asyncio.run(demo_with_actual_events())

    logger.info("\n" + "=" * 60)
    logger.info("✅ All demos completed!")
    logger.info("=" * 60)
    logger.info(
        "\nKey Takeaways:\n"
        "1. Git commit = universal trigger point for all agents\n"
        "2. Works for tool-based (Autonomous) and internal tools (Qwen CLI)\n"
        "3. Batching prevents excessive reindexing\n"
        "4. 100% backward compatible\n"
    )


if __name__ == "__main__":
    main()
