# Staging Environment

module "vpc" {
  source = "../../modules/vpc"

  name_prefix        = local.name_prefix
  vpc_cidr           = var.vpc_cidr
  availability_zones = slice(data.aws_availability_zones.available.names, 0, var.availability_zones_count)
  tags               = local.common_tags
}

module "rds" {
  source = "../../modules/rds"

  name_prefix             = local.name_prefix
  vpc_id                  = module.vpc.vpc_id
  subnet_ids              = module.vpc.private_subnet_ids
  allowed_security_groups = [module.ecs.ecs_security_group_id]

  instance_class        = var.db_instance_class
  allocated_storage     = var.db_allocated_storage
  max_allocated_storage = var.db_max_allocated_storage
  db_name               = var.db_name
  db_username           = var.db_username

  # Staging: single AZ, no deletion protection
  multi_az            = false
  deletion_protection = false

  tags = local.common_tags
}

module "elasticache" {
  source = "../../modules/elasticache"

  name_prefix             = local.name_prefix
  vpc_id                  = module.vpc.vpc_id
  subnet_ids              = module.vpc.private_subnet_ids
  allowed_security_groups = [module.ecs.ecs_security_group_id]

  node_type       = var.redis_node_type
  num_cache_nodes = 1

  tags = local.common_tags
}

module "ecs" {
  source = "../../modules/ecs"

  name_prefix        = local.name_prefix
  vpc_id             = module.vpc.vpc_id
  public_subnet_ids  = module.vpc.public_subnet_ids
  private_subnet_ids = module.vpc.private_subnet_ids

  task_cpu      = var.ecs_task_cpu
  task_memory   = var.ecs_task_memory
  desired_count = 1
  min_capacity  = 1
  max_capacity  = 3

  domain_name     = var.domain_name
  certificate_arn = var.certificate_arn

  environment_variables = {
    DJANGO_SETTINGS_MODULE = "config.settings.staging"
    POSTGRES_HOST          = module.rds.endpoint
    POSTGRES_PORT          = tostring(module.rds.port)
    POSTGRES_DB            = var.db_name
    REDIS_URL              = "redis://${module.elasticache.endpoint}:${module.elasticache.port}/1"
    CELERY_BROKER_URL      = "redis://${module.elasticache.endpoint}:${module.elasticache.port}/0"
  }

  secrets = {
    DJANGO_SECRET_KEY = var.django_secret_key
    POSTGRES_USER     = "${module.rds.secret_arn}:username::"
    POSTGRES_PASSWORD = "${module.rds.secret_arn}:password::"
    SENTRY_DSN        = var.sentry_dsn
  }

  tags = local.common_tags
}
