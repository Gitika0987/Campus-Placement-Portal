#!/bin/bash
# =============================================================
#   FRONTEND DEPLOYMENT TO S3 — deploy_frontend.sh
# =============================================================
#   WHAT IS THIS?
#   This script:
#   1. Updates the API URL in the frontend files to point
#      to your Nginx load balancer's public IP on AWS.
#   2. Creates an S3 bucket configured for static website hosting.
#   3. Uploads the frontend files to S3.
#
#   PREREQUISITES:
#   - AWS CLI installed and configured (aws configure)
#   - Your Nginx EC2 instance's public IP address
#
#   HOW TO USE:
#   chmod +x deploy_frontend.sh
#   ./deploy_frontend.sh <NGINX-PUBLIC-IP> <S3-BUCKET-NAME>
#
#   EXAMPLE:
#   ./deploy_frontend.sh 54.123.45.67 campus-placement-portal-2026
# =============================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# ── Validate arguments ──────────────────────────
if [ -z "$1" ] || [ -z "$2" ]; then
    echo -e "${RED}Usage: ./deploy_frontend.sh <NGINX-PUBLIC-IP> <S3-BUCKET-NAME>${NC}"
    echo "  Example: ./deploy_frontend.sh 54.123.45.67 campus-placement-portal-2026"
    exit 1
fi

NGINX_IP=$1
BUCKET_NAME=$2
BASEDIR="$(cd "$(dirname "$0")" && pwd)"
TEMP_DIR="/tmp/placement-frontend-deploy"

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║   Frontend Deployment to Amazon S3           ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  Nginx IP:    ${YELLOW}$NGINX_IP${NC}"
echo -e "  S3 Bucket:   ${YELLOW}$BUCKET_NAME${NC}"
echo ""

# ── Step 1: Copy frontend files to temp dir ────────
echo -e "${YELLOW}▶ Preparing frontend files...${NC}"
rm -rf "$TEMP_DIR"
mkdir -p "$TEMP_DIR"
cp "$BASEDIR/frontend/index.html" "$TEMP_DIR/"
cp "$BASEDIR/frontend/admin.html" "$TEMP_DIR/"

# ── Step 2: Update API URL to point to Nginx on AWS ──
echo -e "${YELLOW}▶ Updating API URL → http://$NGINX_IP:8080${NC}"
sed -i.bak "s|http://localhost:8080|http://$NGINX_IP:8080|g" "$TEMP_DIR/index.html"
sed -i.bak "s|http://localhost:8080|http://$NGINX_IP:8080|g" "$TEMP_DIR/admin.html"
rm -f "$TEMP_DIR"/*.bak
echo -e "${GREEN}✓ API URLs updated${NC}"

# ── Step 3: Create S3 bucket ──────────────────────
echo ""
echo -e "${YELLOW}▶ Creating S3 bucket: $BUCKET_NAME${NC}"
aws s3 mb "s3://$BUCKET_NAME" 2>/dev/null || echo "  (Bucket may already exist)"

# ── Step 4: Configure bucket for static website ───
echo -e "${YELLOW}▶ Configuring static website hosting...${NC}"
aws s3 website "s3://$BUCKET_NAME" \
    --index-document index.html \
    --error-document index.html

# ── Step 5: Set bucket policy (public read) ────────
echo -e "${YELLOW}▶ Setting public access policy...${NC}"

# Disable block public access
aws s3api put-public-access-block \
    --bucket "$BUCKET_NAME" \
    --public-access-block-configuration \
    "BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false"

# Set bucket policy for public read
cat > /tmp/bucket-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::$BUCKET_NAME/*"
        }
    ]
}
EOF

aws s3api put-bucket-policy --bucket "$BUCKET_NAME" --policy file:///tmp/bucket-policy.json
echo -e "${GREEN}✓ Public access enabled${NC}"

# ── Step 6: Upload files to S3 ────────────────────
echo ""
echo -e "${YELLOW}▶ Uploading frontend to S3...${NC}"
aws s3 sync "$TEMP_DIR/" "s3://$BUCKET_NAME/" \
    --content-type "text/html" \
    --cache-control "max-age=60"

echo -e "${GREEN}✓ Files uploaded${NC}"

# ── Step 7: Get website URL ───────────────────────
REGION=$(aws configure get region 2>/dev/null || echo "us-east-1")
WEBSITE_URL="http://$BUCKET_NAME.s3-website-$REGION.amazonaws.com"

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║   ✓ Frontend Deployed!                       ║${NC}"
echo -e "${CYAN}╠══════════════════════════════════════════════╣${NC}"
echo -e "${CYAN}║${NC}                                              ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  Student Portal:                             ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  ${GREEN}$WEBSITE_URL/index.html${NC}"
echo -e "${CYAN}║${NC}                                              ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  Admin Dashboard:                            ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  ${GREEN}$WEBSITE_URL/admin.html${NC}"
echo -e "${CYAN}║${NC}                                              ${CYAN}║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════╝${NC}"
echo ""

# Cleanup
rm -rf "$TEMP_DIR" /tmp/bucket-policy.json
