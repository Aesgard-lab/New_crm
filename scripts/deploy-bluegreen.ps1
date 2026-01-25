# Blue/Green Deployment Script
# 
# Este script implementa deployments blue/green para zero-downtime
# Usa Docker Compose con dos entornos: blue y green

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("blue", "green")]
    [string]$Target,
    
    [string]$Image = "crm:latest",
    
    [switch]$Rollback,
    
    [switch]$Force
)

$ErrorActionPreference = "Stop"

# Configuration
$NGINX_CONFIG = "nginx/conf.d/upstream.conf"
$HEALTH_ENDPOINT = "/health/ready/"
$HEALTH_TIMEOUT = 120
$HEALTH_INTERVAL = 5

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $color = switch ($Level) {
        "INFO" { "White" }
        "SUCCESS" { "Green" }
        "WARNING" { "Yellow" }
        "ERROR" { "Red" }
    }
    Write-Host "[$timestamp] [$Level] $Message" -ForegroundColor $color
}

function Get-CurrentEnvironment {
    if (Test-Path $NGINX_CONFIG) {
        $content = Get-Content $NGINX_CONFIG -Raw
        if ($content -match "server crm-blue") {
            return "blue"
        }
        elseif ($content -match "server crm-green") {
            return "green"
        }
    }
    return "none"
}

function Wait-ForHealth {
    param(
        [string]$Container,
        [int]$Timeout = $HEALTH_TIMEOUT
    )
    
    $startTime = Get-Date
    $healthy = $false
    
    Write-Log "Waiting for $Container to be healthy..."
    
    while (-not $healthy) {
        $elapsed = ((Get-Date) - $startTime).TotalSeconds
        
        if ($elapsed -gt $Timeout) {
            Write-Log "Health check timeout after $Timeout seconds" "ERROR"
            return $false
        }
        
        try {
            $port = if ($Container -eq "crm-blue") { 8001 } else { 8002 }
            $response = Invoke-WebRequest -Uri "http://localhost:$port$HEALTH_ENDPOINT" -TimeoutSec 5 -UseBasicParsing
            
            if ($response.StatusCode -eq 200) {
                $healthy = $true
                Write-Log "$Container is healthy!" "SUCCESS"
            }
        }
        catch {
            Write-Host "." -NoNewline
            Start-Sleep -Seconds $HEALTH_INTERVAL
        }
    }
    
    return $true
}

function Switch-Traffic {
    param([string]$Target)
    
    $upstreamConfig = @"
# Blue/Green Upstream Configuration
# Generated: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
# Active: $Target

upstream crm_backend {
    server crm-$Target`:8000;
}
"@
    
    $upstreamConfig | Out-File -FilePath $NGINX_CONFIG -Encoding UTF8
    
    Write-Log "Switching traffic to $Target environment"
    
    # Reload nginx
    docker-compose exec -T nginx nginx -s reload
    
    Write-Log "Traffic switched to $Target" "SUCCESS"
}

function Deploy-Environment {
    param(
        [string]$Environment,
        [string]$Image
    )
    
    Write-Log "Deploying to $Environment environment with image $Image"
    
    # Update the image in docker-compose
    $env:CRM_IMAGE = $Image
    
    # Scale down the target environment first
    docker-compose stop "crm-$Environment"
    
    # Pull new image
    Write-Log "Pulling image $Image..."
    docker-compose pull "crm-$Environment"
    
    # Start the new container
    Write-Log "Starting $Environment environment..."
    docker-compose up -d "crm-$Environment"
    
    # Run migrations
    Write-Log "Running migrations..."
    docker-compose exec -T "crm-$Environment" python manage.py migrate --noinput
    
    return $true
}

# Main execution
Write-Log "=== Blue/Green Deployment ===" "INFO"
Write-Log "Target: $Target | Image: $Image"

$currentEnv = Get-CurrentEnvironment
Write-Log "Current active environment: $currentEnv"

if ($Rollback) {
    Write-Log "Rolling back to $Target environment" "WARNING"
    
    if (-not (Wait-ForHealth "crm-$Target")) {
        Write-Log "Target environment is not healthy, cannot rollback" "ERROR"
        exit 1
    }
    
    Switch-Traffic $Target
    Write-Log "Rollback complete!" "SUCCESS"
    exit 0
}

if ($currentEnv -eq $Target -and -not $Force) {
    Write-Log "Target environment $Target is already active. Use -Force to redeploy." "WARNING"
    exit 1
}

# Deploy to target environment
if (-not (Deploy-Environment $Target $Image)) {
    Write-Log "Deployment failed" "ERROR"
    exit 1
}

# Wait for health check
if (-not (Wait-ForHealth "crm-$Target")) {
    Write-Log "Health check failed. Keeping traffic on $currentEnv" "ERROR"
    exit 1
}

# Switch traffic
Switch-Traffic $Target

# Keep old environment running for quick rollback
Write-Log "Keeping $currentEnv environment for rollback capability"

Write-Log "=== Deployment Complete ===" "SUCCESS"
Write-Log "Active environment: $Target"
Write-Log "To rollback: .\deploy.ps1 -Target $currentEnv -Rollback"
