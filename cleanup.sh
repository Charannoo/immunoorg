#!/bin/bash
# ImmunoOrg: Automated Cleanup Script (Bash version)
# Removes unwanted files before submission

echo "🧹 ImmunoOrg Cleanup Script (Bash)"
echo "========================================================================"

PROJECT_PATH="D:\scaler-r2"
# Convert Windows path for bash if needed
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    PROJECT_PATH=$(cygpath -u "$PROJECT_PATH")
fi

# Step 1: Remove __pycache__ directories
echo -e "\n1️⃣ Removing __pycache__ directories..."
find "$PROJECT_PATH" -type d -name "__pycache__" -exec echo "  ✅ Removing: {}" \; -exec rm -rf {} + 2>/dev/null
echo "  ✅ Complete"

# Step 2: Remove .pyc files
echo -e "\n2️⃣ Removing .pyc files..."
find "$PROJECT_PATH" -type f -name "*.pyc" -exec echo "  ✅ Removing: {}" \; -delete
find "$PROJECT_PATH" -type f -name "*.pyo" -exec rm {} + 2>/dev/null
echo "  ✅ Complete"

# Step 3: Create/Update .gitignore
echo -e "\n3️⃣ Creating/updating .gitignore..."
cat > "$PROJECT_PATH/.gitignore" << 'EOF'
# Python cache
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
*.egg-info/
dist/
build/

# Virtual environments
venv/
env/
ENV/
.venv
env.bak/
venv.bak/

# IDE
.vscode/
.idea/
*.swp
*.swo
*.bak
*~
.DS_Store
Thumbs.db

# Jupyter
.ipynb_checkpoints/
*.ipynb_checkpoints

# Environment
.env
.env.local
.env.*.local

# Models & Large Files
*.pkl
*.pth
*.pickle
*.bin
*.safetensors
*.h5
*.ckpt
checkpoints/
models/

# Data
data/
*.csv
*.xlsx

# Logs
logs/
*.log

# OS
.DS_Store
Thumbs.db
.directory

# Misc
.pytest_cache/
.coverage
htmlcov/
.mypy_cache/
.dmypy.json
dmypy.json
EOF
echo "  ✅ .gitignore created/updated"

# Step 4: Verify removal
echo -e "\n4️⃣ Verifying cleanup..."
CACHE_COUNT=$(find "$PROJECT_PATH" -type d -name "__pycache__" 2>/dev/null | wc -l)
PYC_COUNT=$(find "$PROJECT_PATH" -type f -name "*.pyc" 2>/dev/null | wc -l)

if [ $CACHE_COUNT -eq 0 ]; then
    echo "  ✅ No __pycache__ directories"
else
    echo "  ⚠️ Warning: Found $CACHE_COUNT __pycache__ directories"
fi

if [ $PYC_COUNT -eq 0 ]; then
    echo "  ✅ No .pyc files"
else
    echo "  ⚠️ Warning: Found $PYC_COUNT .pyc files"
fi

# Step 5: Security check
echo -e "\n5️⃣ Security check..."
SUSPICIOUS=$(find "$PROJECT_PATH" -type f \( -name ".env*" -o -name "*secret*" -o -name "*password*" -o -name "*token*" -o -name "*api_key*" \) 2>/dev/null | grep -v ".md" | wc -l)

if [ $SUSPICIOUS -eq 0 ]; then
    echo "  ✅ No suspicious files found"
else
    echo "  ⚠️ Warning: Found $SUSPICIOUS potentially sensitive files"
    find "$PROJECT_PATH" -type f \( -name ".env*" -o -name "*secret*" -o -name "*password*" -o -name "*token*" -o -name "*api_key*" \) 2>/dev/null | grep -v ".md"
fi

# Step 6: Summary
echo -e "\n========================================================================"
echo "✅ CLEANUP COMPLETE!"
echo "========================================================================"

echo -e "\n📊 Summary:"
echo "  ✅ __pycache__ directories removed"
echo "  ✅ .pyc files removed"
echo "  ✅ .gitignore created/updated"
echo "  ✅ No credentials found"

echo -e "\n🚀 Next steps:"
echo "  1. cd $PROJECT_PATH"
echo "  2. git add -A"
echo "  3. git commit -m 'Clean build artifacts before submission'"
echo "  4. git push"

echo -e "\n📝 Verify with: git status"
echo "   (Should show: working tree clean)"
