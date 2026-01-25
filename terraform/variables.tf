# Variables globales

variable "aws_region" {
  description = "AWS Region"
  type        = string
  default     = "eu-west-1"
}

variable "project_name" {
  description = "Nombre del proyecto"
  type        = string
  default     = "crm"
}

variable "environment" {
  description = "Entorno (production, staging, development)"
  type        = string
  default     = "production"
}

# VPC Variables
variable "vpc_cidr" {
  description = "CIDR block para VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones_count" {
  description = "Numero de AZs a usar"
  type        = number
  default     = 2
}

# RDS Variables
variable "db_instance_class" {
  description = "Clase de instancia RDS"
  type        = string
  default     = "db.t3.medium"
}

variable "db_allocated_storage" {
  description = "Almacenamiento inicial en GB"
  type        = number
  default     = 20
}

variable "db_max_allocated_storage" {
  description = "Almacenamiento maximo para autoscaling"
  type        = number
  default     = 100
}

variable "db_name" {
  description = "Nombre de la base de datos"
  type        = string
  default     = "crm_db"
}

variable "db_username" {
  description = "Usuario master de la BD"
  type        = string
  default     = "crm_admin"
  sensitive   = true
}

# ElastiCache Variables
variable "redis_node_type" {
  description = "Tipo de nodo Redis"
  type        = string
  default     = "cache.t3.micro"
}

variable "redis_num_cache_nodes" {
  description = "Numero de nodos Redis"
  type        = number
  default     = 1
}

# ECS Variables
variable "ecs_task_cpu" {
  description = "CPU para task de ECS (en unidades)"
  type        = number
  default     = 512
}

variable "ecs_task_memory" {
  description = "Memoria para task de ECS (en MB)"
  type        = number
  default     = 1024
}

variable "ecs_desired_count" {
  description = "Numero deseado de tasks"
  type        = number
  default     = 2
}

variable "ecs_min_capacity" {
  description = "Minimo de tasks para autoscaling"
  type        = number
  default     = 2
}

variable "ecs_max_capacity" {
  description = "Maximo de tasks para autoscaling"
  type        = number
  default     = 10
}

# Application Variables
variable "domain_name" {
  description = "Dominio para la aplicacion"
  type        = string
  default     = ""
}

variable "certificate_arn" {
  description = "ARN del certificado ACM para HTTPS"
  type        = string
  default     = ""
}

# Secrets (usar AWS Secrets Manager o variables de entorno)
variable "django_secret_key" {
  description = "Django SECRET_KEY"
  type        = string
  sensitive   = true
}

variable "sentry_dsn" {
  description = "Sentry DSN"
  type        = string
  default     = ""
  sensitive   = true
}
