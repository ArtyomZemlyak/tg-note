# Verification Steps for Settings Fix

## Pre-Deployment Checklist

### ✅ Code Quality
- [x] All Python files compile successfully
- [x] No syntax errors
- [x] Type hints properly used
- [x] Logging added for debugging

### ✅ Changes Made
- [x] `src/bot/handlers.py` - Per-user components implementation
- [x] `src/bot/settings_handlers.py` - Cache invalidation hooks
- [x] `src/bot/telegram_bot.py` - Initialization order fixed

### ✅ Documentation
- [x] `SETTINGS_FIX_SUMMARY.md` - Technical details (English)
- [x] `SETTINGS_FLOW_DIAGRAM.md` - Flow diagrams (English)
- [x] `ИСПРАВЛЕНИЕ_НАСТРОЕК.md` - User guide (Russian)
- [x] `VERIFICATION_STEPS.md` - This file

## Post-Deployment Testing

### Test 1: MESSAGE_GROUP_TIMEOUT (Critical)

**Objective:** Verify that changed timeout is applied immediately

**Steps:**
1. Start the bot
2. Send a message to get baseline behavior
3. Open settings: `/settings`
4. Navigate to: Processing → MESSAGE_GROUP_TIMEOUT
5. Change from 30 to 10 seconds
6. Send 2-3 messages with 5-second gaps
7. **Expected:** Messages should group and process after ~10 seconds, not 30

**Success Criteria:**
- ✅ Setting change is reflected in menu
- ✅ Next message group uses new 10-second timeout
- ✅ Log shows: "Creating MessageAggregator for user X with timeout 10s"

**Rollback if:**
- ❌ Messages still group after 30 seconds
- ❌ Error messages appear

---

### Test 2: KB_GIT_ENABLED (Important)

**Objective:** Verify Git integration can be toggled per-user

**Steps:**
1. Ensure Git is enabled: `/settings` → Knowledge Base → KB_GIT_ENABLED → Enable
2. Send a test message
3. Check that Git commit was created: `cd knowledge_bases/[kb_name] && git log -1`
4. Go back to settings and disable Git
5. Send another test message
6. **Expected:** No new Git commit is created

**Success Criteria:**
- ✅ Git commits created when enabled
- ✅ No Git commits when disabled
- ✅ Log shows: "Invalidating cache for user X" after toggle

**Rollback if:**
- ❌ Git behavior doesn't change after toggle
- ❌ Error: "git operations failed"

---

### Test 3: Multi-User Isolation

**Objective:** Verify different users can have different settings

**Prerequisites:** Need 2 test users (User A and User B)

**Steps:**
1. User A: Set MESSAGE_GROUP_TIMEOUT to 10
2. User B: Set MESSAGE_GROUP_TIMEOUT to 60
3. Both users send messages simultaneously
4. **Expected:** 
   - User A's messages group after ~10s
   - User B's messages group after ~60s

**Success Criteria:**
- ✅ Each user's timeout is independent
- ✅ Logs show different aggregators: "Creating MessageAggregator for user A with timeout 10s"
- ✅ Logs show different aggregators: "Creating MessageAggregator for user B with timeout 60s"

**Rollback if:**
- ❌ Both users use the same timeout
- ❌ Settings interfere with each other

---

### Test 4: Agent Settings (Advanced)

**Objective:** Verify agent configuration changes apply

**Steps:**
1. Check current agent type: `/settings` → Agent → AGENT_TYPE
2. Note current behavior
3. Change AGENT_TIMEOUT from 300 to 60
4. Send a message that requires agent processing
5. **Expected:** Agent timeout is now 60 seconds instead of 300

**Success Criteria:**
- ✅ Log shows: "Creating agent for user X: [type]"
- ✅ New timeout value is used
- ✅ If processing takes >60s, timeout occurs

**Rollback if:**
- ❌ Agent still uses old timeout
- ❌ Agent creation fails

---

### Test 5: Cache Invalidation

**Objective:** Verify cache is properly cleared on settings change

**Steps:**
1. Send a message (creates cached components)
2. Change any setting via `/settings`
3. Check logs for: "Invalidating cache for user X"
4. Send another message
5. Check logs for: "Creating MessageAggregator for user X" (recreated)

**Success Criteria:**
- ✅ Cache invalidation logged
- ✅ Components recreated with new settings
- ✅ No memory leaks (old components are cleaned up)

**Rollback if:**
- ❌ Cache invalidation not logged
- ❌ Components not recreated
- ❌ Memory usage grows abnormally

---

### Test 6: Settings Reset

**Objective:** Verify `/resetsetting` command works

**Steps:**
1. Change MESSAGE_GROUP_TIMEOUT to 15
2. Send messages, verify 15s timeout works
3. Run: `/resetsetting MESSAGE_GROUP_TIMEOUT`
4. **Expected:** "✅ Setting MESSAGE_GROUP_TIMEOUT reset to default: 30"
5. Send messages, verify 30s timeout is back

**Success Criteria:**
- ✅ Reset command succeeds
- ✅ Default value is restored
- ✅ Cache is invalidated
- ✅ Next message uses default setting

**Rollback if:**
- ❌ Reset doesn't work
- ❌ Old custom value still used

---

## Monitoring

### Key Logs to Watch

**Success indicators:**
```
Creating MessageAggregator for user 123 with timeout 10s
Creating agent for user 123: qwen_code_cli
Invalidating cache for user 123
```

**Warning indicators:**
```
Error creating timeout callback task for chat
Agent processing failed
Failed to save setting
```

**Error indicators:**
```
ModuleNotFoundError
AttributeError: 'BotHandlers' object has no attribute
KeyError in user_message_aggregators
```

### Performance Metrics

Monitor these after deployment:

1. **Memory Usage**
   - Should stay stable (cached components are cleaned up)
   - Per-user caches should grow linearly with active users

2. **Response Time**
   - First message after settings change: slightly slower (cache miss)
   - Subsequent messages: same as before

3. **CPU Usage**
   - Should remain stable
   - Each user has own background task for message aggregation

## Rollback Plan

If critical issues occur:

1. **Quick Rollback:**
   ```bash
   git checkout HEAD~1 -- src/bot/handlers.py
   git checkout HEAD~1 -- src/bot/settings_handlers.py
   git checkout HEAD~1 -- src/bot/telegram_bot.py
   # Restart bot
   ```

2. **Verify rollback:**
   - Bot starts without errors
   - Settings can still be viewed (but won't apply immediately)
   - Message processing works

3. **Investigate:**
   - Check logs for error patterns
   - Verify environment has all dependencies
   - Test in isolated environment

## Success Metrics

After 24 hours of deployment:

- ✅ No critical errors in logs
- ✅ Users can change settings successfully
- ✅ Settings changes take effect immediately (verified by at least 3 users)
- ✅ No memory leaks observed
- ✅ Performance remains stable
- ✅ Multi-user operation works correctly

## Known Limitations

1. **Settings not cached:** Each call to `get_setting()` reads from JSON file
   - Future optimization: Add in-memory cache with TTL
   
2. **No validation on file:** If `user_settings_overrides.json` is corrupted, falls back to defaults
   - Consider adding JSON validation

3. **Background tasks:** Each user gets own message aggregator background task
   - Monitor CPU usage with many concurrent users
   
4. **Agent instances:** Each user gets own agent instance
   - May use significant memory if agent is large
   - Consider implementing agent pooling for very large deployments

## Contact

For issues or questions:
- Check logs in `./logs/bot.log`
- Review documentation files created
- Test in isolated environment before production deployment
