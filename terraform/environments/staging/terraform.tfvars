# Staging Variables

aws_region   = "eu-west-1"
project_name = "crm"
environment  = "staging"

# VPC
vpc_cidr                 = "10.1.0.0/16"
availability_zones_count = 2

# RDS (smaller for staging)
db_instance_class        = "db.t3.micro"
db_allocated_storage     = 10
db_max_allocated_storage = 50
db_name                  = "crm_staging"

# ElastiCache
redis_node_type       = "cache.t3.micro"
redis_num_cache_nodes = 1

# ECS (minimal for staging)
ecs_task_cpu     = 256
ecs_task_memory  = 512
ecs_desired_count = 1
ecs_min_capacity  = 1
ecs_max_capacity  = 3

# Domain
# domain_name     = "staging.crm.tudominio.com"
# certificate_arn = "arn:aws:acm:eu-west-1:123456789:certificate/xxx"
