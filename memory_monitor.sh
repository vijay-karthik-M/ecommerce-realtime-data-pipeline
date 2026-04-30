#!/bin/bash
# ============================================================================
# MEMORY MONITORING DASHBOARD
# ============================================================================
# Real-time monitoring for 8GB RAM laptops running the project
# ============================================================================

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

while true; do
    clear
    
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║          MEMORY MONITORING DASHBOARD - 8GB LAPTOP             ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo ""
    
    # System Memory
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📊 SYSTEM MEMORY"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    MEM_INFO=$(free -h | grep Mem)
    SWAP_INFO=$(free -h | grep Swap)
    
    TOTAL=$(echo $MEM_INFO | awk '{print $2}')
    USED=$(echo $MEM_INFO | awk '{print $3}')
    FREE=$(echo $MEM_INFO | awk '{print $4}')
    AVAILABLE=$(echo $MEM_INFO | awk '{print $7}')
    
    SWAP_TOTAL=$(echo $SWAP_INFO | awk '{print $2}')
    SWAP_USED=$(echo $SWAP_INFO | awk '{print $3}')
    
    echo "Memory:    Total: $TOTAL | Used: $USED | Free: $FREE | Available: $AVAILABLE"
    echo "Swap:      Total: $SWAP_TOTAL | Used: $SWAP_USED"
    
    # Memory percentage
    MEM_PERCENT=$(free | grep Mem | awk '{print int($3/$2 * 100)}')
    
    if [ $MEM_PERCENT -lt 70 ]; then
        echo -e "${GREEN}Status:    ✅ HEALTHY ($MEM_PERCENT% used)${NC}"
    elif [ $MEM_PERCENT -lt 85 ]; then
        echo -e "${YELLOW}Status:    ⚠️  WARNING ($MEM_PERCENT% used)${NC}"
    else
        echo -e "${RED}Status:    🚨 CRITICAL ($MEM_PERCENT% used) - STOP JOBS NOW!${NC}"
    fi
    
    echo ""
    
    # Top Memory Consumers
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🔝 TOP MEMORY PROCESSES"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    printf "%-30s %8s %6s\n" "PROCESS" "MEM%" "MEM"
    ps aux --sort=-%mem | head -6 | tail -5 | awk '{printf "%-30s %8s %6s\n", $11, $4"%", $6/1024"M"}'
    echo ""
    
    # Docker Stats (if running)
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -q .; then
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "🐳 DOCKER CONTAINERS"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}" 2>/dev/null | head -6
        echo ""
    fi
    
    # Spark Jobs (if running)
    SPARK_JOBS=$(ps aux | grep -E "pyspark|spark-submit" | grep -v grep | wc -l)
    if [ $SPARK_JOBS -gt 0 ]; then
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "⚡ SPARK JOBS RUNNING: $SPARK_JOBS"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ps aux | grep -E "pyspark|streaming" | grep -v grep | awk '{printf "%-50s %6s\n", $11, $4"%"}'
        echo ""
    fi
    
    # Warnings
    if [ $MEM_PERCENT -gt 85 ]; then
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo -e "${RED}🚨 CRITICAL WARNING${NC}"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "Memory usage critical! System may freeze."
        echo ""
        echo "IMMEDIATE ACTIONS:"
        echo "  1. Stop Spark job (Ctrl+C in job terminal)"
        echo "  2. Run: sync && echo 3 | sudo tee /proc/sys/vm/drop_caches"
        echo "  3. Close browser tabs"
        echo "  4. Wait 30 seconds before retrying"
        echo ""
    fi
    
    # Recommendations
    FREE_GB=$(echo $AVAILABLE | sed 's/Gi//' | sed 's/Mi//')
    if [[ $AVAILABLE == *"M"* ]]; then
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo -e "${YELLOW}⚠️  LOW MEMORY AVAILABLE${NC}"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "Available memory: $AVAILABLE"
        echo "Recommendation: Wait before starting new Spark jobs"
        echo ""
    fi
    
    # Controls
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Press Ctrl+C to exit | Updating every 2 seconds"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    sleep 2
done
