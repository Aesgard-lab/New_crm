#!/bin/bash
#
# Blue/Green Deployment Script
# 
# Este script implementa deployments blue/green para zero-downtime
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
NGINX_CONFIG="nginx/conf.d/upstream.conf"
HEALTH_ENDPOINT="/health/ready/"
HEALTH_TIMEOUT=120
HEALTH_INTERVAL=5

# Functions
log_info() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] [INFO] $1"
}

log_success() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] ${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] ${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] ${RED}[ERROR]${NC} $1"
}

get_current_env() {
    if [ -f "$NGINX_CONFIG" ]; then
        if grep -q "server crm-blue" "$NGINX_CONFIG"; then
            echo "blue"
        elif grep -q "server crm-green" "$NGINX_CONFIG"; then
            echo "green"
        else
            echo "none"
        fi
    else
        echo "none"
    fi
}

wait_for_health() {
    local container=$1
    local timeout=${2:-$HEALTH_TIMEOUT}
    local start_time=$(date +%s)
    
    log_info "Waiting for $container to be healthy..."
    
    local port
    if [ "$container" == "crm-blue" ]; then
        port=8001
    else
        port=8002
    fi
    
    while true; do
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))
        
        if [ $elapsed -gt $timeout ]; then
            log_error "Health check timeout after $timeout seconds"
            return 1
        fi
        
        if curl -sf "http://localhost:$port$HEALTH_ENDPOINT" > /dev/null 2>&1; then
            log_success "$container is healthy!"
            return 0
        fi
        
        echo -n "."
        sleep $HEALTH_INTERVAL
    done
}

switch_traffic() {
    local target=$1
    
    cat > "$NGINX_CONFIG" << EOF
# Blue/Green Upstream Configuration
# Generated: $(date '+%Y-%m-%d %H:%M:%S')
# Active: $target

upstream crm_backend {
    server crm-$target:8000;
}
EOF
    
    log_info "Switching traffic to $target environment"
    
    # Reload nginx
    docker-compose exec -T nginx nginx -s reload
    
    log_success "Traffic switched to $target"
}

deploy_environment() {
    local environment=$1
    local image=$2
    
    log_info "Deploying to $environment environment with image $image"
    
    # Set environment variable for docker-compose
    export CRM_IMAGE=$image
    
    # Stop the target environment
    docker-compose stop "crm-$environment" || true
    
    # Pull new image
    log_info "Pulling image $image..."
    docker-compose pull "crm-$environment"
    
    # Start the new container
    log_info "Starting $environment environment..."
    docker-compose up -d "crm-$environment"
    
    # Run migrations
    log_info "Running migrations..."
    docker-compose exec -T "crm-$environment" python manage.py migrate --noinput
    
    return 0
}

# Parse arguments
TARGET=""
IMAGE="crm:latest"
ROLLBACK=false
FORCE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--target)
            TARGET="$2"
            shift 2
            ;;
        -i|--image)
            IMAGE="$2"
            shift 2
            ;;
        -r|--rollback)
            ROLLBACK=true
            shift
            ;;
        -f|--force)
            FORCE=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 -t <blue|green> [-i <image>] [-r] [-f]"
            echo ""
            echo "Options:"
            echo "  -t, --target    Target environment (blue or green)"
            echo "  -i, --image     Docker image to deploy (default: crm:latest)"
            echo "  -r, --rollback  Rollback to target environment"
            echo "  -f, --force     Force deployment even if target is active"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Validate target
if [ -z "$TARGET" ]; then
    log_error "Target environment is required. Use -t blue or -t green"
    exit 1
fi

if [ "$TARGET" != "blue" ] && [ "$TARGET" != "green" ]; then
    log_error "Invalid target: $TARGET. Must be 'blue' or 'green'"
    exit 1
fi

# Main execution
log_info "=== Blue/Green Deployment ==="
log_info "Target: $TARGET | Image: $IMAGE"

CURRENT_ENV=$(get_current_env)
log_info "Current active environment: $CURRENT_ENV"

if [ "$ROLLBACK" = true ]; then
    log_warning "Rolling back to $TARGET environment"
    
    if ! wait_for_health "crm-$TARGET"; then
        log_error "Target environment is not healthy, cannot rollback"
        exit 1
    fi
    
    switch_traffic "$TARGET"
    log_success "Rollback complete!"
    exit 0
fi

if [ "$CURRENT_ENV" == "$TARGET" ] && [ "$FORCE" = false ]; then
    log_warning "Target environment $TARGET is already active. Use -f to force redeploy."
    exit 1
fi

# Deploy to target environment
if ! deploy_environment "$TARGET" "$IMAGE"; then
    log_error "Deployment failed"
    exit 1
fi

# Wait for health check
if ! wait_for_health "crm-$TARGET"; then
    log_error "Health check failed. Keeping traffic on $CURRENT_ENV"
    exit 1
fi

# Switch traffic
switch_traffic "$TARGET"

# Keep old environment running for quick rollback
log_info "Keeping $CURRENT_ENV environment for rollback capability"

log_success "=== Deployment Complete ==="
log_info "Active environment: $TARGET"
log_info "To rollback: ./deploy-bluegreen.sh -t $CURRENT_ENV -r"
