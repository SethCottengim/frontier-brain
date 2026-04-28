#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_DIR="$HOME/.claude"
DECISIONS_DIR="$CLAUDE_DIR/decisions"
BRAIN_BIN="$CLAUDE_DIR/frontier-brain/bin"
BRAIN_LIB="$CLAUDE_DIR/frontier-brain/lib"
HOOKS_DIR="$CLAUDE_DIR/hooks/frontier-brain"
SETTINGS="$CLAUDE_DIR/settings.json"

echo "=== frontier-brain installer ==="
echo "User: ${USER:-unknown}"
echo "Source: $SCRIPT_DIR"
echo ""

# Create directories
mkdir -p "$DECISIONS_DIR" "$BRAIN_BIN/static" "$BRAIN_LIB" "$HOOKS_DIR"

# Copy files
cp "$SCRIPT_DIR/bin/decision-engine.py" "$BRAIN_BIN/"
cp "$SCRIPT_DIR/bin/visualize.py" "$BRAIN_BIN/"
cp "$SCRIPT_DIR/bin/static/d3.v7.min.js" "$BRAIN_BIN/static/"
cp "$SCRIPT_DIR/lib/graphdb.py" "$BRAIN_LIB/"
cp "$SCRIPT_DIR/lib/router.py" "$BRAIN_LIB/"
cp "$SCRIPT_DIR/hooks/decision-detect.js" "$HOOKS_DIR/"

chmod +x "$BRAIN_BIN/decision-engine.py" "$BRAIN_BIN/visualize.py"

echo "Files installed:"
echo "  $BRAIN_BIN/decision-engine.py"
echo "  $BRAIN_BIN/visualize.py"
echo "  $BRAIN_BIN/static/d3.v7.min.js"
echo "  $BRAIN_LIB/graphdb.py"
echo "  $BRAIN_LIB/router.py"
echo "  $HOOKS_DIR/decision-detect.js"
echo ""

# Register hook in settings.json (merge, don't clobber)
if [ ! -f "$SETTINGS" ]; then
    echo '{}' > "$SETTINGS"
fi

HOOK_CMD="node \"$HOOKS_DIR/decision-detect.js\""

# Check if hook already registered
if python3 -c "
import json, sys
with open('$SETTINGS') as f:
    s = json.load(f)
hooks = s.get('hooks', {}).get('UserPromptSubmit', [])
for h in hooks:
    entries = h.get('hooks', [])
    for e in entries:
        if 'decision-detect' in e.get('command', ''):
            sys.exit(0)
sys.exit(1)
" 2>/dev/null; then
    echo "Hook already registered in settings.json"
else
    python3 -c "
import json

settings_path = '$SETTINGS'
hook_cmd = '$HOOK_CMD'

with open(settings_path) as f:
    s = json.load(f)

if 'hooks' not in s:
    s['hooks'] = {}

ups = s['hooks'].get('UserPromptSubmit', [])
ups.append({
    'matcher': '',
    'hooks': [{
        'type': 'command',
        'command': hook_cmd,
        'timeout': 5
    }]
})
s['hooks']['UserPromptSubmit'] = ups

with open(settings_path, 'w') as f:
    json.dump(s, f, indent=2)
"
    echo "Hook registered in settings.json"
fi
echo ""

# Initialize brain.db
python3 "$BRAIN_BIN/decision-engine.py" index
echo ""

echo "=== Installation complete ==="
echo "Decisions dir: $DECISIONS_DIR"
echo "Brain DB: $DECISIONS_DIR/brain.db"
echo "Run 'python3 $BRAIN_BIN/decision-engine.py --help' for commands"
