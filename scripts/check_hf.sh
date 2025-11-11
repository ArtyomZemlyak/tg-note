#!/bin/bash
# Diagnostic script to check HuggingFace accessibility

echo "═══════════════════════════════════════════════════════════════"
echo "Checking HuggingFace Accessibility"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Check basic connectivity
echo "1. Checking basic internet connectivity..."
echo "───────────────────────────────────────────────────────────────"
if ping -c 3 8.8.8.8 > /dev/null 2>&1; then
    echo "✅ Internet connection: OK"
else
    echo "❌ Internet connection: FAILED"
    echo "   Cannot reach 8.8.8.8"
fi
echo ""

# Check DNS resolution
echo "2. Checking DNS resolution..."
echo "───────────────────────────────────────────────────────────────"
for domain in huggingface.co cdn-lfs.huggingface.co cas-bridge.xethub.hf.co; do
    if nslookup $domain > /dev/null 2>&1; then
        echo "✅ DNS for $domain: OK"
    else
        echo "❌ DNS for $domain: FAILED"
    fi
done
echo ""

# Check HuggingFace main site
echo "3. Checking HuggingFace main site..."
echo "───────────────────────────────────────────────────────────────"
response=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 https://huggingface.co 2>&1)
if [ "$response" = "200" ]; then
    echo "✅ huggingface.co: Accessible (HTTP $response)"
else
    echo "❌ huggingface.co: Not accessible (HTTP $response)"
fi
echo ""

# Check CDN
echo "4. Checking HuggingFace CDN..."
echo "───────────────────────────────────────────────────────────────"
response=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 https://cdn-lfs.huggingface.co 2>&1)
if [ "$response" = "200" ] || [ "$response" = "403" ]; then
    echo "✅ cdn-lfs.huggingface.co: Accessible (HTTP $response)"
else
    echo "❌ cdn-lfs.huggingface.co: Not accessible (HTTP $response)"
fi
echo ""

# Check XET Bridge
echo "5. Checking XET Bridge..."
echo "───────────────────────────────────────────────────────────────"
response=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 https://cas-bridge.xethub.hf.co 2>&1)
if [ "$response" = "200" ] || [ "$response" = "403" ]; then
    echo "✅ cas-bridge.xethub.hf.co: Accessible (HTTP $response)"
else
    echo "❌ cas-bridge.xethub.hf.co: Not accessible (HTTP $response)"
    echo "   ⚠️  This is the server that was timing out!"
fi
echo ""

# Check download speed
echo "6. Checking download speed to HuggingFace..."
echo "───────────────────────────────────────────────────────────────"
echo "Downloading small test file..."
speed=$(curl -w "%{speed_download}" -o /dev/null -s --connect-timeout 10 --max-time 30 \
    https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/transformers/model_doc/bert_architecture.png 2>&1)
if [ $? -eq 0 ]; then
    speed_kb=$(echo "scale=2; $speed / 1024" | bc)
    echo "✅ Download speed: ${speed_kb} KB/s"

    if (( $(echo "$speed_kb < 10" | bc -l) )); then
        echo "   ⚠️  Speed is very slow (< 10 KB/s) - possible throttling or regional restrictions"
    elif (( $(echo "$speed_kb < 100" | bc -l) )); then
        echo "   ⚠️  Speed is slow (< 100 KB/s) - might have issues with large files"
    else
        echo "   ✅ Speed looks good"
    fi
else
    echo "❌ Download test: FAILED"
fi
echo ""

# Check geographical location
echo "7. Checking your location (via ipinfo.io)..."
echo "───────────────────────────────────────────────────────────────"
location=$(curl -s --connect-timeout 5 https://ipinfo.io/json 2>&1)
if [ $? -eq 0 ]; then
    echo "$location" | python3 -m json.tool 2>/dev/null || echo "$location"
else
    echo "⚠️  Could not detect location"
fi
echo ""

# Summary
echo "═══════════════════════════════════════════════════════════════"
echo "Summary & Recommendations"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Check if likely regional restriction
if [ "$response" != "200" ] || (( $(echo "$speed_kb < 10" | bc -l 2>/dev/null || echo "0") )); then
    echo "🚨 LIKELY REGIONAL RESTRICTIONS DETECTED!"
    echo ""
    echo "Solutions:"
    echo "  1. Use ModelScope mirror (for China/Asia)"
    echo "  2. Use VPN to bypass restrictions"
    echo "  3. Use proxy server"
    echo "  4. Ask someone to download and share via direct link"
    echo ""
    echo "Try ModelScope:"
    echo "  pip install modelscope"
    echo "  # Then use ModelScope downloads instead"
else
    echo "✅ No obvious regional restrictions detected"
    echo ""
    echo "If still having issues, try:"
    echo "  1. Use VPN/proxy temporarily"
    echo "  2. Download at different time (less congestion)"
    echo "  3. Use alternative source (ModelScope, Kaggle, etc.)"
fi
echo ""
