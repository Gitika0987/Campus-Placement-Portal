#!/bin/bash
# =============================================================
#   START ALL SERVERS — start.sh
# =============================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

BASEDIR="$(cd "$(dirname "$0")" && pwd)"

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║     Campus Placement Portal — Startup        ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  Base dir: ${YELLOW}$BASEDIR${NC}"
echo ""

if ! command -v python3 &>/dev/null; then
    echo -e "${RED}✗ Python3 not found.${NC}"; exit 1
fi
echo -e "${GREEN}✓ Python3 found${NC}"

# Activate virtual environment if it exists
if [ -d "$BASEDIR/venv" ]; then
    source "$BASEDIR/venv/bin/activate"
    echo -e "${GREEN}✓ Virtual environment activated${NC}"
fi

if [ ! -f "$BASEDIR/backend/placement.db" ]; then
    echo -e "${YELLOW}⚙ Database not found. Creating it...${NC}"
    python3 "$BASEDIR/backend/init_db.py"
    echo -e "${GREEN}✓ Database created${NC}"
else
    echo -e "${GREEN}✓ Database exists${NC}"
fi

echo -e "${YELLOW}⚙ Clearing ports 5001, 5002, 5003, 8080...${NC}"
for port in 5001 5002 5003 8080; do
    lsof -ti:$port | xargs kill -9 2>/dev/null || true
done
sleep 1
echo -e "${GREEN}✓ Ports cleared${NC}"

echo ""
echo -e "${BLUE}▶ Starting Flask backend instances...${NC}"

python3 "$BASEDIR/backend/app.py" 5001 > /tmp/flask_5001.log 2>&1 &
PID1=$!
echo -e "  ${GREEN}✓ Backend :5001 started (PID $PID1)${NC}"

python3 "$BASEDIR/backend/app.py" 5002 > /tmp/flask_5002.log 2>&1 &
PID2=$!
echo -e "  ${GREEN}✓ Backend :5002 started (PID $PID2)${NC}"

python3 "$BASEDIR/backend/app.py" 5003 > /tmp/flask_5003.log 2>&1 &
PID3=$!
echo -e "  ${GREEN}✓ Backend :5003 started (PID $PID3)${NC}"

sleep 2

echo ""
echo -e "${BLUE}▶ Verifying backend health...${NC}"
for port in 5001 5002 5003; do
    if curl -s "http://localhost:$port/health" > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓ :$port is healthy${NC}"
    else
        echo -e "  ${RED}✗ :$port not responding — check /tmp/flask_$port.log${NC}"
    fi
done

echo ""
echo -e "${BLUE}▶ Starting Custom Load Balancer on :8080...${NC}"

python3 "$BASEDIR/backend/load_balancer.py" 8080 > /tmp/load_balancer.log 2>&1 &
PID_LB=$!
sleep 1

if curl -s "http://localhost:8080/health" > /dev/null 2>&1; then
    echo -e "  ${GREEN}✓ Load Balancer started on :8080 (PID $PID_LB)${NC}"
else
    echo -e "  ${YELLOW}⚠ Load Balancer starting... (PID $PID_LB)${NC}"
fi

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║           Everything is running!             ║${NC}"
echo -e "${CYAN}╠══════════════════════════════════════════════╣${NC}"
echo -e "${CYAN}║${NC}  Student Portal : http://localhost:8080       ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  Admin Dashboard: http://localhost:8080/admin.html ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}                                              ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  Load Balancer  : http://localhost:8080      ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  Backend 1      : http://localhost:5001      ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  Backend 2      : http://localhost:5002      ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  Backend 3      : http://localhost:5003      ${CYAN}║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  Press ${RED}Ctrl+C${NC} to stop everything"
echo ""

cleanup() {
    echo ""
    echo -e "${YELLOW}⚙ Shutting down...${NC}"
    kill $PID1 $PID2 $PID3 $PID_LB 2>/dev/null
    echo -e "${GREEN}✓ All servers stopped.${NC}"
    exit 0
}
trap cleanup INT TERM

echo -e "${BLUE}▶ Load Balancer log (watch port rotation!):${NC}"
echo -e "${YELLOW}────────────────────────────────────────────────────${NC}"
sleep 1
tail -f /tmp/load_balancer.log 2>/dev/null &

wait $PID1
