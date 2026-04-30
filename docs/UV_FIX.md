# 🔧 UV INSTALLATION - SIMPLIFIED APPROACH

## 🎯 THE ISSUE YOU HIT

The error occurred because:
1. **pyproject.toml** expects a Python package structure (with `__init__.py` files)
2. **Our project** is organized as scripts (simpler, more practical for learning)
3. **Hatchling** (the build tool) got confused about what to package

## ✅ THE SOLUTION: Use requirements.txt

For script-based projects, **requirements.txt is simpler and better**!

---

## 🚀 CORRECTED INSTALLATION STEPS

### **Step 1: Navigate to Project**
```bash
cd ~/data-engineering-projects/ecommerce-streaming-platform-uv
```

### **Step 2: Activate Virtual Environment**
```bash
# If you haven't created one yet:
uv venv

# Activate it
source .venv/bin/activate
```

### **Step 3: Install Core Dependencies**
```bash
# Install from requirements.txt
uv pip install -r requirements.txt
```

**This installs:**
- kafka-python (Kafka client)
- psycopg2-binary (PostgreSQL)
- pandas, numpy (data processing)
- faker (data generation)
- great-expectations (data quality)
- requests, rich, click (utilities)
- And all other essentials

**Time:** 1-2 minutes

### **Step 4: (Optional) Install Development Tools**
```bash
# Only if you want linting, testing tools
uv pip install -r requirements-dev.txt
```

### **Step 5: (Later) Install Spark**
```bash
# Don't install now - wait until Week 3-4
# Large download (~500MB)
uv pip install -r requirements-spark.txt
```

### **Step 6: Verify Installation**
```bash
# Test imports
python3 -c "import kafka; print('✓ Kafka OK')"
python3 -c "import psycopg2; print('✓ PostgreSQL OK')"
python3 -c "import pandas; print('✓ Pandas OK')"
python3 -c "import faker; print('✓ Faker OK')"
python3 -c "import requests; print('✓ Requests OK')"
```

If all print "✓ ... OK", you're good! ✅

---

## 📋 UPDATED PROJECT FILES

Your project now has these dependency files:

```
ecommerce-streaming-platform/
├── requirements.txt              # Core dependencies (use this!)
├── requirements-dev.txt          # Development tools (optional)
├── requirements-spark.txt        # Spark (install later)
├── pyproject.toml               # Keep for metadata, but don't use for install
└── ... other files
```

---

## 🎯 WHY THIS IS BETTER

### **requirements.txt Approach:**
✅ Simple and straightforward
✅ Industry standard (everyone knows it)
✅ Works with UV, pip, poetry, etc.
✅ No package structure needed
✅ Perfect for script-based projects

### **pyproject.toml Approach:**
- Better for publishing to PyPI
- Better for creating reusable libraries
- Requires proper package structure
- Overkill for learning projects

**For this project:** requirements.txt is the right choice! 🎯

---

## 🔄 COMPLETE WORKFLOW

### **Every Time You Work:**
```bash
# 1. Navigate to project
cd ~/data-engineering-projects/ecommerce-streaming-platform-uv

# 2. Activate venv
source .venv/bin/activate

# 3. You're ready!
python3 test_setup.py
```

### **Adding New Packages:**
```bash
# Method 1: Add to requirements.txt, then:
uv pip install -r requirements.txt

# Method 2: Install directly
uv pip install package-name

# Method 3: Update requirements.txt with current packages
uv pip freeze > requirements-frozen.txt
```

---

## 📝 UPDATED DAY 1 CHECKLIST

- [ ] Project extracted
- [ ] Virtual environment created: `uv venv`
- [ ] Virtual environment activated: `source .venv/bin/activate`
- [ ] Core dependencies installed: `uv pip install -r requirements.txt`
- [ ] Imports work: Test with python -c commands above
- [ ] Docker services running: `cd docker && docker-compose up -d`
- [ ] Tests pass: `python3 test_setup.py`

---

## 🎓 INTERVIEW TIP

If asked about dependency management:

> "I use requirements.txt for dependency management, which is the industry standard. For more complex projects that need to be published as packages, I use pyproject.toml with proper package structure. I also use virtual environments to isolate dependencies and ensure reproducibility across environments."

This shows you understand **when to use which tool** - a sign of experience!

---

## 💡 SUMMARY

**OLD COMMAND (that failed):**
```bash
uv pip install -e ".[dev,spark]"  # ❌ Needed package structure
```

**NEW COMMAND (works perfectly):**
```bash
uv pip install -r requirements.txt  # ✅ Simple and works!
```

**That's it! Much simpler! 🚀**

---

## 🚀 READY TO CONTINUE?

Now that dependencies are installed:

1. **Start Docker services:** `cd docker && docker-compose up -d`
2. **Wait 2 minutes** for services to initialize
3. **Run tests:** `cd .. && python3 test_setup.py`
4. **When tests pass:** You've completed Day 1! 🎉

Questions? Ask before proceeding!
