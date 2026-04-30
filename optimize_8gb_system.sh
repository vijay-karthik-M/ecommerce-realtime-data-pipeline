#!/bin/bash
# ============================================================================
# AUTOMATIC 8GB RAM OPTIMIZATION SCRIPT
# ============================================================================
# Run this to automatically optimize your system for the project
# ============================================================================

set -e  # Exit on error

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║     8GB RAM LAPTOP OPTIMIZATION - AUTOMATIC SETUP              ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running on 8GB system
TOTAL_RAM=$(free -m | grep Mem | awk '{print $2}')
if [ $TOTAL_RAM -gt 10000 ]; then
    echo -e "${YELLOW}⚠️  Your system has ${TOTAL_RAM}MB RAM${NC}"
    echo "This script is for 8GB systems. Your system may not need optimization."
    read -p "Continue anyway? (y/N): " confirm
    if [ "$confirm" != "y" ]; then
        exit 0
    fi
fi

echo -e "${GREEN}System RAM: ${TOTAL_RAM}MB${NC}"
echo ""

# Step 1: Stop everything
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 1: Stopping existing services"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -f "docker/docker-compose.yml" ]; then
    docker compose -f docker/docker-compose.yml down 2>/dev/null || true
fi

pkill -9 python3 2>/dev/null || true
echo -e "${GREEN}✅ Services stopped${NC}"
echo ""

# Step 2: Clear memory cache
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 2: Clearing memory cache"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

sync
echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null
echo -e "${GREEN}✅ Memory cache cleared${NC}"
echo ""

# Step 3: Check/Create Swap
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 3: Configuring swap space"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

SWAP_SIZE=$(free -m | grep Swap | awk '{print $2}')

if [ $SWAP_SIZE -lt 4000 ]; then
    echo "Current swap: ${SWAP_SIZE}MB (need 4GB)"
    
    if [ ! -f /swapfile ]; then
        echo "Creating 4GB swap file..."
        sudo fallocate -l 4G /swapfile
        sudo chmod 600 /swapfile
        sudo mkswap /swapfile
        sudo swapon /swapfile
        
        # Make permanent
        if ! grep -q '/swapfile' /etc/fstab; then
            echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
        fi
        
        echo -e "${GREEN}✅ Swap created: 4GB${NC}"
    else
        echo -e "${YELLOW}⚠️  /swapfile exists but not enabled${NC}"
        sudo swapon /swapfile
        echo -e "${GREEN}✅ Swap enabled${NC}"
    fi
else
    echo -e "${GREEN}✅ Swap already configured: ${SWAP_SIZE}MB${NC}"
fi
echo ""

# Step 4: Configure swappiness
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 4: Optimizing swappiness"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

CURRENT_SWAPPINESS=$(cat /proc/sys/vm/swappiness)
echo "Current swappiness: $CURRENT_SWAPPINESS"

if [ $CURRENT_SWAPPINESS -ne 10 ]; then
    sudo sysctl vm.swappiness=10
    
    if ! grep -q 'vm.swappiness=10' /etc/sysctl.conf; then
        echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf
    fi
    echo -e "${GREEN}✅ Swappiness set to 10${NC}"
else
    echo -e "${GREEN}✅ Swappiness already optimized${NC}"
fi
echo ""

# Step 5: Backup and replace config files
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 5: Optimizing configuration files"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Backup originals
if [ -f "streaming/utils/spark_session.py" ] && [ ! -f "streaming/utils/spark_session.py.ORIGINAL" ]; then
    cp streaming/utils/spark_session.py streaming/utils/spark_session.py.ORIGINAL
    echo "Backed up: spark_session.py"
fi

if [ -f "docker/docker-compose.yml" ] && [ ! -f "docker/docker-compose.yml.ORIGINAL" ]; then
    cp docker/docker-compose.yml docker/docker-compose.yml.ORIGINAL
    echo "Backed up: docker-compose.yml"
fi

if [ -f "data_generator/config.py" ] && [ ! -f "data_generator/config.py.ORIGINAL" ]; then
    cp data_generator/config.py data_generator/config.py.ORIGINAL
    echo "Backed up: config.py"
fi

echo -e "${GREEN}✅ Original files backed up${NC}"
echo ""
echo -e "${YELLOW}⚠️  NOTE: You need to manually copy the optimized config files:${NC}"
echo "   1. spark_session_LOW_MEMORY.py → streaming/utils/spark_session.py"
echo "   2. docker-compose-LOW-MEMORY.yml → docker/docker-compose.yml"
echo "   3. config_LOW_MEMORY.py → data_generator/config.py"
echo ""

# Step 6: Install monitoring tools
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 6: Installing monitoring tools"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if ! command -v htop &> /dev/null; then
    echo "Installing htop..."
    sudo apt-get update -qq
    sudo apt-get install -y htop
fi

echo -e "${GREEN}✅ Monitoring tools ready${NC}"
echo ""

# Step 7: Clean Docker
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 7: Cleaning Docker resources"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

docker system prune -f > /dev/null
echo -e "${GREEN}✅ Docker cleaned${NC}"
echo ""

# Final status
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                  OPTIMIZATION COMPLETE                         ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

echo "📊 SYSTEM STATUS:"
free -h | grep -E "Mem|Swap"
echo ""

echo "✅ COMPLETED OPTIMIZATIONS:"
echo "   • Services stopped"
echo "   • Memory cache cleared"
echo "   • Swap configured (4GB)"
echo "   • Swappiness optimized (10)"
echo "   • Config files backed up"
echo "   • Monitoring tools installed"
echo "   • Docker cleaned"
echo ""

echo "⚠️  NEXT STEPS:"
echo "   1. Copy the 3 optimized config files (see above)"
echo "   2. Run: docker compose -f docker/docker-compose.yml up -d"
echo "   3. Follow sequential execution guide"
echo "   4. Monitor with: watch -n 1 free -h"
echo ""

echo "📚 READ: 8GB_RAM_OPTIMIZATION_GUIDE.md for full details"
echo ""

echo -e "${GREEN}System is ready for optimized execution!${NC}"
