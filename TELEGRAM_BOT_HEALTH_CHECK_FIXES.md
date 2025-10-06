# Telegram Bot Health Check Fixes

## Problem Summary

The Telegram bot was experiencing connection timeout issues that were being exacerbated by the health check and restart mechanism:

1. **Long timeout periods**: Health checks were timing out after 300 seconds (5 minutes), blocking the main event loop
2. **No exponential backoff**: The bot attempted to restart every 30 seconds regardless of previous failures
3. **Infinite retry loop**: No limit on consecutive restart attempts, causing resource exhaustion
4. **Poor error recovery**: Failed restarts would immediately retry without considering the underlying issue

## Root Cause

The errors in the logs show:
- `ClientConnectorError` - Unable to connect to Telegram API
- `ServerDisconnectedError` - Connection dropped by Telegram servers
- `Request timeout` after 300 seconds - Default timeout too long for health checks

These are typically caused by:
- Network connectivity issues
- Telegram API unavailability
- Firewall/proxy blocking connections
- Invalid or revoked bot token

## Implemented Fixes

### 1. Shortened Health Check Timeout (`src/bot/telegram_bot.py`)

**Before:**
```python
async def is_healthy(self) -> bool:
    try:
        await self.bot.get_me()  # Uses default 300s timeout
        return True
    except Exception:
        return False
```

**After:**
```python
async def is_healthy(self, timeout: int = 10) -> bool:
    """Check if bot is healthy with configurable timeout"""
    try:
        await asyncio.wait_for(
            self.bot.get_me(),
            timeout=timeout  # Default 10s, configurable
        )
        return True
    except asyncio.TimeoutError:
        logger.warning(f"Health check timed out after {timeout}s")
        return False
    except Exception as e:
        logger.warning(f"Health check failed: {e}")
        return False
```

**Benefits:**
- Health checks now timeout in 10 seconds instead of 300 seconds
- Better error logging with specific timeout messages
- Configurable timeout for different scenarios

### 2. Added Timeout to Bot Startup (`src/bot/telegram_bot.py`)

**Before:**
```python
bot_info = await self.bot.get_me()  # Uses default 300s timeout
```

**After:**
```python
bot_info = await asyncio.wait_for(
    self.bot.get_me(),
    timeout=30  # 30 second timeout for initial connection
)
```

**Benefits:**
- Faster failure detection during startup
- Prevents long blocking periods during connection issues

### 3. Implemented Exponential Backoff (`main.py`)

**Before:**
```python
if not await telegram_bot.is_healthy():
    logger.warning("Bot health check failed, attempting restart...")
    await telegram_bot.stop()
    await asyncio.sleep(5)  # Fixed 5 second wait
    await telegram_bot.start()
```

**After:**
```python
consecutive_failures = 0
max_consecutive_failures = 5
base_backoff = 5
max_backoff = 300

if not await telegram_bot.is_healthy(timeout=10):
    consecutive_failures += 1
    
    if consecutive_failures >= max_consecutive_failures:
        logger.error("Max failures reached. Manual intervention required.")
        continue  # Stop trying to restart
    
    # Exponential backoff: 5s, 10s, 20s, 40s, 80s (capped at 300s)
    backoff = min(base_backoff * (2 ** (consecutive_failures - 1)), max_backoff)
    
    logger.warning(f"Attempting restart after {backoff}s backoff...")
    await telegram_bot.stop()
    await asyncio.sleep(backoff)
    await telegram_bot.start()
```

**Benefits:**
- Reduces server load by spacing out retry attempts
- Prevents rapid restart loops during prolonged outages
- Allows time for transient issues to resolve

### 4. Added Maximum Retry Limit (`main.py`)

**Before:**
- Unlimited restart attempts
- Could exhaust resources during prolonged outages

**After:**
- Maximum 5 consecutive failures before stopping automatic restarts
- Clear error messages indicating manual intervention needed
- Helpful diagnostics about possible causes

**Benefits:**
- Prevents infinite resource consumption
- Alerts administrators to persistent issues
- Provides actionable troubleshooting information

### 5. Improved Error Messages

**Added:**
- Specific timeout error handling
- Failure attempt tracking (e.g., "attempt 3/5")
- Helpful diagnostic messages:
  ```
  Possible causes: network issues, Telegram API unavailable,
  invalid bot token, or firewall blocking connection.
  ```

## Backoff Schedule

The exponential backoff follows this schedule:

| Attempt | Backoff Time | Total Wait Time |
|---------|--------------|-----------------|
| 1       | 5s           | 5s              |
| 2       | 10s          | 15s             |
| 3       | 20s          | 35s             |
| 4       | 40s          | 75s             |
| 5       | 80s          | 155s            |

After 5 failures, automatic restarts stop to prevent resource exhaustion.

## Testing the Fixes

To verify the fixes work correctly:

1. **Simulate network failure:**
   ```bash
   # Block Telegram API temporarily
   sudo iptables -A OUTPUT -d api.telegram.org -j DROP
   ```

2. **Monitor logs:**
   - Should see: "Health check timed out after 10s" (not 300s)
   - Should see: Exponential backoff messages
   - Should see: Max failures message after 5 attempts

3. **Restore network:**
   ```bash
   sudo iptables -D OUTPUT -d api.telegram.org -j DROP
   ```
   - Bot should detect health restoration
   - Failure counter should reset

## Migration Notes

- **No configuration changes required** - All improvements use sensible defaults
- **Backward compatible** - `is_healthy()` default timeout is 10s but configurable
- **No database changes** - All state is in-memory

## Future Improvements

Consider adding:
1. **Configurable health check parameters** in `config.yaml`:
   ```yaml
   health_check:
     interval: 30
     timeout: 10
     max_failures: 5
     base_backoff: 5
     max_backoff: 300
   ```

2. **Health check metrics** for monitoring:
   - Total health checks performed
   - Failure rate
   - Average response time
   - Restart attempts

3. **Alerting** when max failures reached:
   - Email/SMS notifications
   - Slack/Discord webhooks
   - PagerDuty integration

4. **Circuit breaker pattern** for more sophisticated failure handling

## Troubleshooting

If you continue seeing connection errors:

1. **Check network connectivity:**
   ```bash
   curl -I https://api.telegram.org
   ```

2. **Verify bot token:**
   ```bash
   curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getMe"
   ```

3. **Check firewall rules:**
   ```bash
   sudo iptables -L -n | grep api.telegram.org
   ```

4. **Test with different timeout values:**
   ```python
   # In main.py, adjust:
   if not await telegram_bot.is_healthy(timeout=30):  # Increase if needed
   ```

5. **Use a proxy** if behind corporate firewall:
   - Configure `aiohttp` to use proxy
   - Set proxy in bot initialization

## Summary

These fixes transform the health check system from a liability that made connection issues worse into a robust recovery mechanism that:
- ✅ Detects failures quickly (10s vs 300s)
- ✅ Implements intelligent retry logic (exponential backoff)
- ✅ Prevents resource exhaustion (max 5 attempts)
- ✅ Provides actionable diagnostics
- ✅ Recovers automatically when issues resolve
