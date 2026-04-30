# 📘 DAY 1 EXECUTION GUIDE

## 🎯 What We're Accomplishing Today

By the end of Day 1, you will have:
- ✅ A running Docker environment with 4 services
- ✅ Kafka accepting and storing messages
- ✅ PostgreSQL with analytics database schema
- ✅ Grafana ready for dashboards
- ✅ Understanding of how containers communicate

**Time Required:** 2-3 hours (including reading and understanding)

---

## 🚀 STEP-BY-STEP EXECUTION

### Step 1: Prerequisites Check

**What you need installed on your machine:**

1. **Docker Desktop**
   - Download: https://www.docker.com/products/docker-desktop
   - Why? Runs containers on your local machine
   - Check: `docker --version` (should show version 20.x or higher)

2. **Docker Compose**
   - Usually comes with Docker Desktop
   - Check: `docker-compose --version`

3. **Python 3.8+**
   - Check: `python3 --version`

4. **pip (Python package manager)**
   - Check: `pip3 --version`

**Install required Python libraries:**
```bash
pip3 install kafka-python psycopg2-binary requests
```

**WHY THESE LIBRARIES?**
- `kafka-python`: Interact with Kafka from Python
- `psycopg2-binary`: Connect to PostgreSQL
- `requests`: Make HTTP requests (for Grafana health check)

---

### Step 2: Navigate to Project Directory

```bash
# If you haven't already, create the project from the files I provided
cd /path/to/ecommerce-streaming-platform

# Verify structure
ls -la
# You should see: docker/, README.md, test_setup.py
```

---

### Step 3: Start Docker Services

```bash
cd docker

# Start all services in detached mode (background)
docker-compose up -d
```

**WHAT HAPPENS HERE?**
1. Docker downloads images (first time only - may take 5-10 minutes)
2. Creates containers for each service
3. Creates networks for communication
4. Creates volumes for data persistence
5. Starts containers in dependency order (Zookeeper → Kafka → others)

**CHECK THE OUTPUT:**
You should see:
```
Creating network "docker_data-platform" ... done
Creating volume "docker_zookeeper-data" ... done
Creating volume "docker_kafka-data" ... done
Creating volume "docker_postgres-data" ... done
Creating volume "docker_grafana-data" ... done
Creating zookeeper ... done
Creating postgres ... done
Creating kafka ... done
Creating grafana ... done
```

---

### Step 4: Verify Services Are Running

```bash
# Check status of all containers
docker-compose ps
```

**EXPECTED OUTPUT:**
All services should show "Up" status:
```
Name                State           Ports
--------------------------------------------------------------
kafka              Up              0.0.0.0:9092->9092/tcp
postgres           Up              0.0.0.0:5432->5432/tcp
zookeeper          Up              0.0.0.0:2181->2181/tcp
grafana            Up              0.0.0.0:3000->3000/tcp
```

**IF A SERVICE IS NOT UP:**
```bash
# Check logs for that service
docker-compose logs kafka        # Replace 'kafka' with your service name
docker-compose logs -f kafka     # Follow logs in real-time (Ctrl+C to exit)
```

---

### Step 5: Wait for Services to Be Ready

**IMPORTANT:** Services need time to initialize.

- Zookeeper: ~10 seconds
- Kafka: ~30 seconds (waits for Zookeeper)
- PostgreSQL: ~15 seconds
- Grafana: ~20 seconds

**Good practice:** Wait 1-2 minutes after `docker-compose up -d`

```bash
# You can watch the logs to see when services are ready
docker-compose logs -f kafka
# Look for: "Kafka Server started"
# Press Ctrl+C to stop following logs
```

---

### Step 6: Run Test Suite

```bash
# Go back to project root
cd ..

# Run the test script
python3 test_setup.py
```

**WHAT THIS TESTS:**
1. **Kafka Test:**
   - Can connect to broker?
   - Can create topics?
   - Can produce messages?
   - Can consume messages?

2. **PostgreSQL Test:**
   - Can connect to database?
   - Are schemas created?
   - Are tables created?
   - Is date dimension populated?

3. **Grafana Test:**
   - Is web interface accessible?
   - Is health endpoint responding?

**IF ALL TESTS PASS:** 🎉 You're done with Day 1!

**IF TESTS FAIL:** See troubleshooting section below.

---

## 🔍 MANUAL VERIFICATION (Optional but Recommended)

### Explore Kafka

```bash
# Get a shell inside Kafka container
docker exec -it kafka bash

# List topics
kafka-topics --list --bootstrap-server localhost:9092

# Create a test topic manually
kafka-topics --create --topic my-test-topic --partitions 3 --replication-factor 1 --bootstrap-server localhost:9092

# Produce a message (type a message and press Enter, Ctrl+C to exit)
kafka-console-producer --topic my-test-topic --bootstrap-server localhost:9092

# Consume messages (in another terminal window)
kafka-console-consumer --topic my-test-topic --from-beginning --bootstrap-server localhost:9092

# Exit container shell
exit
```

**CONCEPT: What You're Seeing**
- Topics are like database tables for events
- Producers write, consumers read
- Messages are stored durably (survive restarts)

---

### Explore PostgreSQL

```bash
# Get a shell inside PostgreSQL container
docker exec -it postgres psql -U dataeng -d analytics

# List schemas
\dn

# List tables in analytics schema
\dt analytics.*

# Query date dimension
SELECT date_actual, day_name, is_weekend 
FROM analytics.dim_date 
WHERE date_actual = CURRENT_DATE;

# Count rows in dim_date
SELECT COUNT(*) FROM analytics.dim_date;

# Exit psql
\q
```

**CONCEPT: What You're Seeing**
- Star schema (dimensions + facts)
- Pre-populated date dimension
- Ready for analytics queries

---

### Explore Grafana

Open browser and go to: **http://localhost:3000**

**Login credentials:**
- Username: `admin`
- Password: `admin123`

**First Login:**
1. Grafana will ask to change password (skip for now)
2. You'll see the home dashboard
3. No dashboards yet (we'll create them later)

**Explore:**
- Click ⚙️ (Settings) → Data Sources
- Click "Add data source"
- See PostgreSQL option (we'll configure this later)

---

## 🐛 TROUBLESHOOTING

### Problem: Port Already in Use

**Error:**
```
ERROR: for postgres  Cannot start service postgres: Ports are not available: listen tcp 0.0.0.0:5432: bind: address already in use
```

**Solution:**
```bash
# Find what's using the port
lsof -i :5432        # On Mac/Linux
netstat -ano | findstr :5432    # On Windows

# Stop the conflicting service or change port in docker-compose.yml
# To change port, edit docker-compose.yml:
ports:
  - "5433:5432"  # Use 5433 on host instead of 5432
```

---

### Problem: Container Keeps Restarting

**Check:**
```bash
docker-compose ps
# If you see "Restarting", check logs
docker-compose logs kafka
```

**Common causes:**
1. **Zookeeper not ready** - Wait longer
2. **Config error** - Check environment variables
3. **Port conflict** - Change port in docker-compose.yml

---

### Problem: Can't Connect from Python

**Error:**
```
kafka.errors.NoBrokersAvailable: NoBrokersAvailable
```

**Solution:**
```bash
# 1. Verify Kafka is running
docker-compose ps kafka

# 2. Check Kafka logs
docker-compose logs kafka | grep -i error

# 3. Make sure using localhost:9092 (not kafka:9092)
# localhost = from your machine
# kafka:9092 = from inside Docker network

# 4. Wait 30-60 seconds for Kafka to fully start
```

---

### Problem: PostgreSQL Init Script Didn't Run

**Symptom:** Tables don't exist

**Solution:**
```bash
# Stop and remove containers AND volumes (fresh start)
docker-compose down -v

# Start again
docker-compose up -d

# Wait 30 seconds, then check
docker exec -it postgres psql -U dataeng -d analytics -c "\dt analytics.*"
```

**WHY?** Init scripts only run when database is created first time.
Removing volumes forces recreation.

---

## 📚 KEY CONCEPTS LEARNED TODAY

### 1. Containers vs Virtual Machines
- **Container:** Lightweight, shares host OS kernel, starts in seconds
- **VM:** Full OS, heavy, starts in minutes
- **Use case:** Containers for microservices, VMs for different OSes

### 2. Docker Compose
- **Purpose:** Orchestrate multiple containers
- **Alternative:** Kubernetes (for production at scale)
- **Why not Kubernetes for dev?** Too complex for local development

### 3. Kafka Listeners (Advanced)
```
KAFKA_LISTENERS: PLAINTEXT://0.0.0.0:9092
KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
```
- **LISTENERS:** Where Kafka listens (inside container)
- **ADVERTISED:** What address Kafka tells clients to use
- **Why different?** Allows both internal (Docker) and external (your machine) access

### 4. PostgreSQL Schemas
- **Schema:** Namespace for organizing tables
- **Like folders:** analytics/, staging/, metrics/
- **Why?** Separation of concerns, permission management

### 5. Health Checks
```yaml
healthcheck:
  test: ["CMD", "nc", "-z", "localhost", "2181"]
  interval: 10s
```
- **Purpose:** Verify service is truly ready (not just started)
- **Docker uses this:** Other services wait for healthy status
- **Production:** Critical for orchestration (Kubernetes, ECS)

---

## ✅ DAY 1 COMPLETION CHECKLIST

- [ ] Docker Desktop installed and running
- [ ] All 4 services show "Up" status
- [ ] Test script passes all tests
- [ ] Can access Grafana UI at http://localhost:3000
- [ ] Can see tables in PostgreSQL
- [ ] Understand why we use Docker
- [ ] Understand the role of each service

**IF ALL CHECKED:** You're ready for Day 2! 🎉

---

## 🎓 INTERVIEW PREPARATION

### Question: "Explain your development environment setup"

**Your Answer:**
> "I use Docker Compose to create reproducible environments. I containerize all services—Kafka, Spark, PostgreSQL—so anyone can run `docker-compose up` and have an identical environment. This eliminates 'works on my machine' problems and mirrors production deployments. I also implement health checks so services wait for dependencies to be truly ready before starting."

### Question: "How do you debug when a service won't start?"

**Your Answer:**
> "I follow a systematic approach:
> 1. Check container status with `docker-compose ps`
> 2. Review logs with `docker-compose logs [service]`
> 3. Verify ports aren't conflicting with `lsof` or `netstat`
> 4. Check health check status
> 5. If needed, get a shell with `docker exec -it [container] bash` to debug interactively
> 6. For persistent issues, do a clean restart with `docker-compose down -v` to remove volumes"

### Question: "Why use Kafka instead of a database for events?"

**Your Answer:**
> "Kafka provides several advantages for event streaming:
> 1. **Durability:** Events persisted to disk, can be replayed
> 2. **Scalability:** Handles millions of events per second across partitions
> 3. **Decoupling:** Multiple consumers can read independently
> 4. **Ordering:** Guarantees order within partitions
> 5. **Retention:** Configurable retention for time-travel capabilities
> 
> A database is optimized for queries, not for high-throughput event ingestion. Kafka is built specifically for event streaming."

---

## 🚀 NEXT: DAY 2 PREVIEW

Tomorrow we'll build:
1. **Data Generator** - Simulates realistic e-commerce events
2. **Event Schemas** - Define what our events look like
3. **Producer Script** - Sends events to Kafka

**Concepts we'll learn:**
- Synthetic data generation
- JSON schema design
- Kafka producer patterns
- Realistic data modeling

---

## 💡 FINAL TIPS

1. **Save terminal outputs** - Screenshot successful tests for your portfolio
2. **Document issues** - Keep notes on problems and solutions
3. **Experiment** - Try breaking things! Best way to learn
4. **Ask questions** - If something doesn't make sense, ask before moving on

---

**Congratulations on completing Day 1! 🎉**

Your foundation is solid. Rest, review the concepts, and come back ready for Day 2!
