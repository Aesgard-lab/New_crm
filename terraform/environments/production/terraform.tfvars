# Production Variables

aws_region   = "eu-west-1"
project_name = "crm"
environment  = "production"

# VPC
vpc_cidr                 = "10.0.0.0/16"
availability_zones_count = 2

# RDS
db_instance_class        = "db.t3.medium"
db_allocated_storage     = 20
db_max_allocated_storage = 100
db_name                  = "crm_production"
# db_username            = "crm_admin"  # Set via TF_VAR_db_username

# ElastiCache
redis_node_type       = "cache.t3.micro"
redis_num_cache_nodes = 1

# ECS
ecs_task_cpu     = 512
ecs_task_memory  = 1024
ecs_desired_count = 2
ecs_min_capacity  = 2
ecs_max_capacity  = 10

# Domain (configurar cuando tengas el dominio)
# domain_name     = "crm.tudominio.com"
# certificate_arn = "arn:aws:acm:eu-west-1:123456789:certificate/xxx"

# Secrets (configurar via variables de entorno)
# export TF_VAR_django_secret_key="tu-clave-secreta"
# export TF_VAR_db_username="crm_admin"
# export TF_VAR_sentry_dsn="https://xxx@sentry.io/xxx"
