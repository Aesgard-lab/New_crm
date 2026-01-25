# Outputs principales

output "vpc_id" {
  description = "ID de la VPC"
  value       = module.vpc.vpc_id
}

output "public_subnet_ids" {
  description = "IDs de subnets publicas"
  value       = module.vpc.public_subnet_ids
}

output "private_subnet_ids" {
  description = "IDs de subnets privadas"
  value       = module.vpc.private_subnet_ids
}

output "rds_endpoint" {
  description = "Endpoint de RDS"
  value       = module.rds.endpoint
}

output "rds_port" {
  description = "Puerto de RDS"
  value       = module.rds.port
}

output "redis_endpoint" {
  description = "Endpoint de Redis"
  value       = module.elasticache.endpoint
}

output "redis_port" {
  description = "Puerto de Redis"
  value       = module.elasticache.port
}

output "alb_dns_name" {
  description = "DNS del Application Load Balancer"
  value       = module.ecs.alb_dns_name
}

output "ecs_cluster_name" {
  description = "Nombre del cluster ECS"
  value       = module.ecs.cluster_name
}

output "ecs_service_name" {
  description = "Nombre del servicio ECS"
  value       = module.ecs.service_name
}

output "ecr_repository_url" {
  description = "URL del repositorio ECR"
  value       = module.ecs.ecr_repository_url
}
