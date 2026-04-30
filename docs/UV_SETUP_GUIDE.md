# 🚀 UV PACKAGE MANAGER SETUP GUIDE

## 📚 WHAT IS UV?

**UV** is a next-generation Python package manager written in Rust.

**Advantages over pip:**
- ⚡ **10-100x faster** (parallel downloads, better caching)
- 🔒 **Better dependency resolution** (finds compatible versions)
- 📦 **Lock files** (exact reproducibility)
- 🎯 **Modern workflow** (simpler commands)

**Interview Tip:** 
> "I use UV for faster dependency management and reproducible builds. Its lock file approach ensures the exact same package versions across all environments."

---

## 🎯 COMPLETE UV SETUP FOR THIS PROJECT

### **Step 1: Extract Project Files**

```bash
# Extract the downloaded archive
cd ~/data-engineering-projects
tar -xzf ecommerce-streaming-platform-day1.tar.gz
cd ecommerce-streaming-platform
```

---

### **Step 2: Initialize UV (if not already done)**

```bash
# Initialize UV in the project directory
uv init

# This creates:
# - .venv/ (virtual environment)
# - .python-version (specifies Python version)
# - May create pyproject.toml (we already have one)
```

**What's happening?**
- UV detects you want a virtual environment
- Creates `.venv` directory with isolated Python
- All packages install here (not globally)

---

### **Step 3: Activate Virtual Environment**

```bash
# On macOS/Linux:
source .venv/bin/activate

# On Windows:
.venv\Scripts\activate

# Your prompt should change to show (.venv)
# Like: (.venv) user@machine:~/project$
```

**Why activate?**
- Python commands now use the virtual environment
- Packages install in `.venv/`, not system-wide
- Can deactivate with: `deactivate`

**IMPORTANT:** You need to activate the venv every time you open a new terminal.

---

### **Step 4: Install Dependencies**

Now that you have `pyproject.toml`, install dependencies:

```bash
# Option A: Basic installation (just what we need for Day 1)
uv pip install -e .

# Option B: Include development tools (recommended)
uv pip install -e ".[dev]"

# Option C: Include Spark (for later weeks - heavy download)
uv pip install -e ".[dev,spark]"
```

**What does `-e .` mean?**
- `-e` = "editable mode" (changes to code reflect immediately)
- `.` = current directory (where pyproject.toml is)

**First install takes 1-2 minutes:**
- UV downloads packages
- Compiles any native extensions
- Creates lock information

---

### **Step 5: Verify Installation**

```bash
# Check installed packages
uv pip list

# You should see:
# kafka-python       2.0.2
# psycopg2-binary    2.9.9
# requests           2.31.0
# ... and more

# Test imports
python3 -c "import kafka; print('Kafka OK')"
python3 -c "import psycopg2; print('PostgreSQL OK')"
python3 -c "import requests; print('Requests OK')"
```

**If all print "OK":** ✅ Dependencies installed correctly!

---

### **Step 6: Update the Updated Project Archive**

I've added `pyproject.toml` to your project. You'll want this file:

```bash
# This file is now part of your project
ls pyproject.toml

# If missing, I'll provide it in a new archive
```

---

## 📂 YOUR PROJECT STRUCTURE NOW

```
ecommerce-streaming-platform/
├── .venv/                      # Virtual environment (don't commit to git)
├── .python-version             # Python version (e.g., 3.11)
├── pyproject.toml             # Dependencies and config
├── docker/
│   ├── docker-compose.yml
│   └── init-scripts/
│       └── 01_init_db.sql
├── test_setup.py
├── docs/
│   └── DAY_1_GUIDE.md
└── README.md
```

---

## 🔄 DAILY WORKFLOW WITH UV

### **Every Time You Open Terminal:**

```bash
cd ~/data-engineering-projects/ecommerce-streaming-platform
source .venv/bin/activate  # Activate virtual environment
```

### **Running Scripts:**

```bash
# Make sure venv is activated first
python3 test_setup.py

# Or use UV directly (auto-uses .venv)
uv run python test_setup.py
```

### **Adding New Packages Later:**

```bash
# Add to pyproject.toml dependencies, then:
uv pip install -e .

# OR install directly:
uv pip install package-name
```

### **Freezing Exact Versions (for deployment):**

```bash
# Create requirements.txt with exact versions
uv pip freeze > requirements.txt

# Or create a lock file (better approach)
uv pip compile pyproject.toml -o requirements.lock
```

---

## 🎯 UV vs PIP vs POETRY - COMPARISON

| Feature | UV | pip | poetry |
|---------|----|----|--------|
| Speed | ⚡⚡⚡ | ⚡ | ⚡⚡ |
| Dependency Resolution | ✅ Best | ❌ Basic | ✅ Good |
| Lock Files | ✅ Yes | ❌ No | ✅ Yes |
| Written In | Rust | Python | Python |
| Learning Curve | Easy | Easy | Medium |
| Industry Adoption | Growing | Universal | Common |

**For this project:** UV is perfect - fast, modern, simple.

**For job applications:** Know pip too (still industry standard).

---

## 🐛 TROUBLESHOOTING UV ISSUES

### **Issue: `uv: command not found`**

```bash
# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or with pip
pip install uv

# Verify
uv --version
```

---

### **Issue: Virtual Environment Not Activating**

```bash
# Make sure you're in project directory
pwd  # Should show: /path/to/ecommerce-streaming-platform

# Try explicit activation
source .venv/bin/activate

# Check if Python is from venv
which python3
# Should show: /path/to/ecommerce-streaming-platform/.venv/bin/python3
```

---

### **Issue: Package Import Fails**

```bash
# Check if venv is activated
# Prompt should show: (.venv)

# Reinstall dependencies
uv pip install -e .

# Check installation
uv pip list | grep kafka
```

---

### **Issue: Conflicting Python Versions**

```bash
# UV uses Python from .python-version file
cat .python-version

# To use specific Python version:
echo "3.11" > .python-version
uv init --python 3.11

# Or explicitly:
uv venv --python 3.11
```

---

## 📝 UPDATED DAY 1 CHECKLIST

- [ ] UV installed: `uv --version`
- [ ] Project extracted
- [ ] `uv init` run in project directory
- [ ] Virtual environment activated (see `.venv` in prompt)
- [ ] Dependencies installed: `uv pip install -e ".[dev]"`
- [ ] Imports working: `python3 -c "import kafka"`
- [ ] Docker services running: `docker-compose ps`
- [ ] Tests passing: `python3 test_setup.py`

---

## 🎓 INTERVIEW TALKING POINTS

### "Why do you use virtual environments?"

> "Virtual environments isolate project dependencies, preventing conflicts between projects. Each project can have different package versions without affecting others. It also ensures reproducibility - anyone can recreate the exact environment using the dependency specification."

### "What's the advantage of UV over pip?"

> "UV is 10-100x faster due to parallel downloads and better caching. It has superior dependency resolution that prevents version conflicts. UV also supports lock files out of the box for reproducible builds, which is critical in production environments."

### "How do you ensure reproducible builds?"

> "I use pyproject.toml to specify dependencies and UV's lock files to freeze exact versions. I also containerize with Docker so the entire environment - not just Python packages - is reproducible. This ensures dev, staging, and production are identical."

---

## 🚀 NEXT STEPS

1. **Complete the setup above**
2. **Run the test suite:** `python3 test_setup.py`
3. **If all tests pass:** You're ready to proceed!
4. **If tests fail:** Review the main DAY_1_GUIDE.md troubleshooting section

---

## 💡 PRO TIPS

1. **Always activate venv first** - Make it a habit
2. **Use `uv run`** - Automatically uses correct venv: `uv run python script.py`
3. **Pin major versions** - In production, use exact versions
4. **Commit pyproject.toml** - Don't commit .venv/ (add to .gitignore)
5. **Update regularly** - `uv pip install --upgrade -e .`

---

## 🎯 FINAL COMMAND SUMMARY

```bash
# Setup (once)
cd ecommerce-streaming-platform
uv init
uv pip install -e ".[dev]"

# Daily workflow
source .venv/bin/activate
python3 test_setup.py

# Add package
uv pip install package-name

# Deactivate when done
deactivate
```

---

**You're all set with UV! This is a more modern, professional approach. Great choice! 🚀**
