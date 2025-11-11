# 🎯 Final Solution: Docling Model Path Issues

## Executive Summary

Fixed **critical** model path configuration issues causing:
```
FileNotFoundError: /opt/docling-mcp/models/model.safetensors
```

### Root Causes Found

1. **❌ Wrong Repository Folder**: Docling's `download_model_bundles()` used outdated `repo_id` (`docling-project/...`) instead of preset `repo_id` (`docling-models/...`)
2. **❌ Missing Folder Check**: When model folder doesn't exist, LayoutModel falls back to base directory
3. **❌ Late Environment Setup**: Environment variables set after Docling imports
4. **❌ Network Error Handling**: No graceful fallback to cached models

## ✅ Complete Fix Implemented

### 1. Direct HuggingFace Download (model_sync.py)

**What changed**: Layout models now download directly from HuggingFace using **preset's `repo_id`**, not Docling's defaults.

**Why**: Ensures correct folder name:
- ✅ **Now**: `docling-models--layout__v2` (from preset `docling-models/layout__v2`)
- ❌ **Before**: `docling-project--docling-layout-heron` (from Docling defaults)

**Code**:
```python
# Extract repo_id from our preset
repo_id = layout_spec.repo_id  # "docling-models/layout__v2"
model_repo_folder = layout_spec.model_repo_folder  # "docling-models--layout__v2"

# Download directly to correct folder
target_dir = base_dir / model_repo_folder
_snapshot_download_with_hf_transfer_fallback(
    repo_id=repo_id,
    target_dir=target_dir,
    ...
)
```

### 2. Enhanced Cache Fallback (model_sync.py)

**What changed**: When network fails, check if models exist locally before raising error.

**Why**: Handles connection errors gracefully (like "RemoteDisconnected").

**Code**:
```python
def _check_models_exist(directory: Path) -> bool:
    """Check for *.safetensors, *.onnx, *.bin, *.pt, config.json"""
    ...

try:
    return snapshot_download(**kwargs)
except Exception:
    if _check_models_exist(target_dir):
        logger.warning("Using cached models")
        return str(target_dir)  # ✅ Use cache
    raise  # Only error if truly missing
```

### 3. Early Environment Setup (env_setup.py - NEW)

**What changed**: Created module that sets environment variables **before** any Docling imports.

**Why**: Docling initializes on first import and reads env vars then.

**Usage**:
```python
# First import in every module using Docling
import tg_docling.env_setup  # Sets DOCLING_MODELS_DIR, etc.
from docling.datamodel import ...  # Now env is ready
```

### 4. Better Path Configuration (server.py, tools.py)

**What changed**: Use direct assignment instead of `setdefault()` for environment variables.

**Why**: Ensures correct values even if previously set incorrectly.

**Code**:
```python
# ❌ Before
os.environ.setdefault("DOCLING_MODELS_DIR", str(models_dir))

# ✅ After
os.environ["DOCLING_MODELS_DIR"] = str(models_dir)
```

## 📊 How It Works Now

### Startup Flow

```
1. Import tg_docling module
   ↓
2. env_setup runs (sets DOCLING_MODELS_DIR=/opt/docling-mcp/models)
   ↓
3. Docling imports (reads env vars)
   ↓
4. Startup sync downloads models
   ├─ Uses preset repo_id: "docling-models/layout__v2"
   ├─ Downloads to: /opt/docling-mcp/models/docling-models--layout__v2/
   └─ Files: model.safetensors, config.json, etc.
   ↓
5. Converter initialization
   ├─ artifacts_path = /opt/docling-mcp/models (base dir)
   ├─ model_repo_folder = "docling-models--layout__v2"
   └─ Checks: (artifacts_path / model_repo_folder).exists() → ✅ True!
   ↓
6. LayoutPredictor receives: /opt/docling-mcp/models/docling-models--layout__v2/
   ↓
7. Finds: model.safetensors ✅
```

### Path Construction (Docling Internal)

```python
# In LayoutModel.__init__
artifacts_path = Path("/opt/docling-mcp/models")      # From env
model_repo_folder = "docling-models--layout__v2"      # From preset
model_path = ""                                        # Usually empty

# Check if folder exists
if (artifacts_path / model_repo_folder).exists():     # ✅ NOW TRUE!
    final_path = artifacts_path / model_repo_folder / model_path
    # = /opt/docling-mcp/models/docling-models--layout__v2

# LayoutPredictor looks for:
# /opt/docling-mcp/models/docling-models--layout__v2/model.safetensors ✅
```

## 🧪 Verification Steps

### 1. Rebuild Container

```bash
docker-compose down
docker-compose build docling-mcp
docker-compose up -d docling-mcp
```

### 2. Check Logs

```bash
docker-compose logs -f docling-mcp
```

**Look for**:
```
✅ Docling environment configured: DOCLING_MODELS_DIR=/opt/docling-mcp/models
✅ Downloading Docling layout bundle: preset='layout_v2', 
   repo_id='docling-models/layout__v2', folder='docling-models--layout__v2'
✅ Downloading layout model from docling-models/layout__v2 to ...
✅ Model sync completed successfully
```

### 3. Verify Model Files

```bash
docker-compose exec docling-mcp ls -la /opt/docling-mcp/models/
```

**Should show**:
```
docling-models--layout__v2/           ← ✅ Correct folder!
docling-models--tableformer/          ← Other models
...
```

**Should NOT show**:
```
docling-project--docling-layout-heron/   ← ❌ Old/wrong folder
```

### 4. Check Model Contents

```bash
docker-compose exec docling-mcp ls /opt/docling-mcp/models/docling-models--layout__v2/
```

**Should show**:
```
model.safetensors
config.json
preprocessor_config.json
```

### 5. Test Conversion

Send a PDF to your Telegram bot. Should now convert successfully!

## 📚 Documentation

1. **`CRITICAL_FIX.md`** - Detailed technical analysis
2. **`DOCLING_MODEL_PATH_FIX.md`** - Complete implementation guide
3. **`QUICK_START.md`** - Quick setup instructions
4. **`FINAL_SOLUTION.md`** (this file) - Executive summary

## 🔧 Files Modified

```
docker/docling-mcp/app/tg_docling/
├── env_setup.py         (NEW) - Early environment setup
├── model_sync.py        (MOD) - Direct HuggingFace download + cache fallback
├── server.py            (MOD) - Import env_setup + better path config
├── tools.py             (MOD) - Import env_setup + directory creation
├── config.py            (MOD) - Import env_setup
└── converter.py         (MOD) - Import env_setup

docker/docling-mcp/
├── CRITICAL_FIX.md      (NEW) - Technical analysis
├── DOCLING_MODEL_PATH_FIX.md (NEW) - Implementation guide
├── QUICK_START.md       (NEW) - Quick reference
└── FINAL_SOLUTION.md    (NEW) - Executive summary
```

## ⚙️ Configuration

No configuration changes needed! The fix works with default settings:

```yaml
# config.yaml (no changes needed)
MEDIA_PROCESSING_DOCLING:
  backend: mcp
  startup_sync: true
  pipeline:
    layout:
      preset: layout_v2  # ✅ Will use correct repo_id now
```

## 🚀 Migration from Old Setup

If you have old model folders, clean them up:

```bash
# Optional: Remove old/wrong model folders
docker-compose exec docling-mcp find /opt/docling-mcp/models -name "docling-project--*" -type d -exec rm -rf {} +

# Fresh start
docker-compose down
docker-compose build docling-mcp
docker-compose up -d docling-mcp
```

## ✨ Benefits

1. **✅ Correct Model Paths**: Uses preset `repo_id`, not Docling defaults
2. **✅ Network Resilience**: Graceful fallback to cached models
3. **✅ Reliable Startup**: Environment configured before Docling imports
4. **✅ Better Logging**: Detailed debug information
5. **✅ No Configuration Changes**: Works with existing setup

## 🐛 Troubleshooting

### Still seeing errors?

1. **Check folder name**:
   ```bash
   docker-compose exec docling-mcp ls /opt/docling-mcp/models/
   ```
   Should show `docling-models--layout__v2`, not `docling-project--*`

2. **Force re-download**:
   ```bash
   docker-compose exec docling-mcp python -m tg_docling.model_sync --force
   ```

3. **Check environment**:
   ```bash
   docker-compose exec docling-mcp env | grep DOCLING
   ```
   Should show:
   ```
   DOCLING_MODELS_DIR=/opt/docling-mcp/models
   DOCLING_ARTIFACTS_PATH=/opt/docling-mcp/models
   ```

### Network errors?

System now handles them gracefully. If models are cached, conversion will work even when HuggingFace Hub is unreachable.

## 🎉 Success Criteria

✅ **Before**: `FileNotFoundError: /opt/docling-mcp/models/model.safetensors`  
✅ **After**: Document conversion works, even with network issues!

---

**Questions?** Check the detailed docs:
- Technical analysis → `CRITICAL_FIX.md`
- Implementation guide → `DOCLING_MODEL_PATH_FIX.md`
- Quick reference → `QUICK_START.md`
