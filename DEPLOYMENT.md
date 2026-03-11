# Deploy TJDFT API - Docker Swarm + Traefik

Guia de deploy para Docker Swarm com Portainer e Traefik.

## Pré-requisitos

- **Docker Engine 20.10+** com Swarm habilitado
- **Cluster Docker Swarm funcionando** (mínimo 1 manager, 1 worker recomendado)
- **Recursos mínimos:** 2 vCPU, 4GB RAM por nó
- **Portas:** 80, 443 (Traefik), 2377 (Swarm), 7946 (Swarm)
- **Traefik v2+** configurado com:
  - Entrypoints: `web` (porta 80) e `websecure` (porta 443)
  - CertResolver LetsEncrypt configurado
  - Rede overlay `traefik-public` criada
- Acesso ao Portainer (opcional, para gerenciamento visual)

## Primeira Configuração

### 1. Configurar Traefik

Se ainda não tiver Traefik no swarm, deploy primeiro:

```bash
docker network create --driver=overlay --attachable traefik-public

docker stack deploy -c traefik.yml traefik
```

### 2. Criar rede para a aplicação

```bash
docker network create --driver=overlay --attachable tjdft-network
```

### 3. Atualizar `docker-compose.swarm.yml`

Altere as seguintes configurações:

- **Domínio:** `api.seu-dominio.com.br` → seu domínio real
- **Registro Docker:** `prof-ramos` → seu usuário DockerHub
- **CertResolver:** `letsencrypt` → nome do seu certresolver Traefik

## Deploy

### Opção 1: Script automático

```bash
./deploy-swarm.sh 1.0.0
```

### Opção 2: Manual

```bash
# 1. Build e push da imagem multi-arch
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t prof-ramos/tjdft-api:latest \
  --push .

# 2. Deploy no swarm
docker stack deploy -c docker-compose.swarm.yml tjdft
```

### Via Portainer

1. Acesse Portainer → Stacks
2. Add stack
3. Name: `tjdft`
4. Upload `docker-compose.swarm.yml`
5. Deploy the stack

## Verificar Deploy

```bash
# Status dos serviços
docker stack services tjdft

# Logs da API (Swarm)
docker service logs -f tjdft_api

# Status das tasks
docker stack ps tjdft

# Inspecionar serviço
docker service inspect tjdft_api --pretty
```

## Atualizar Aplicação

```bash
# Nova versão
./deploy-swarm.sh 1.1.0

# Ou manual
docker buildx build --platform linux/amd64,linux/arm64 \
  -t prof-ramos/tjdft-api:1.1.0 --push .
docker stack deploy -c docker-compose.swarm.yml tjdft
```

## Troubleshooting

### Serviço não inicia

```bash
# Ver logs
docker service logs tjdft_api --tail 100

# Ver detalhes da task
docker service ps tjdft_api --no-trunc
```

### Erro de conexão com banco

```bash
# Entrar no container (Swarm - usar docker compose ou task ID)
docker service ps tjdft_api
# Copie a NODE e ID da task, depois:
docker exec -it <task_id> sh

# Ou usando docker compose (dev)
docker compose exec api sh
ls -la /app/data/
```

### Traefik não roteia

1. Verifique labels no serviço:
```bash
docker service inspect tjdft_api --format '{{json .Spec.Labels}}' | jq
```

2. Ver dashboard Traefik para erros de roteamento

### Escalar para mais réplicas

**ATENÇÃO:** SQLite não suporta múltiplas réplicas! Para escalar, migre para PostgreSQL/MySQL.

```bash
# Para PostgreSQL, escalaria assim:
docker service scale tjdft_api=4
```

## Backup do Banco

```bash
# Opção 1: Via volume (recomendado)
docker run --rm -v tjdft-data:/data -v "$(pwd)":/backup \
  alpine tar czf /backup/tjdft-db-$(date +%Y%m%d).tar.gz /data/

# Opção 2: Copiar arquivo do container (development)
docker compose cp api:/app/data/tjdft.db ./backup-$(date +%Y%m%d).db
```

### Restaurar Backup

```bash
# Parar serviço
docker service scale tjdft_api=0

# Restaurar volume
docker run --rm -v tjdft-data:/data -v "$(pwd)":/backup \
  alpine tar xzf /backup/tjdft-db-YYYYMMDD.tar.gz -C /

# Reiniciar serviço
docker service scale tjdft_api=1
```

**Recomendação:** Configure backups automáticos com retenção de 7 dias.

## Estrutura de Arquivos

```
.
├── Dockerfile                  # Multi-stage build
├── .dockerignore              # Arquivos ignorados no build
├── docker-compose.swarm.yml   # Swarm stack (produção)
├── docker-compose.dev.yml     # Desenvolvimento local
├── deploy-swarm.sh            # Script de deploy
├── Makefile                   # Comandos Docker úteis
└── nginx.conf.example         # Exemplo nginx (não usado com Traefik)
```

## Labels Traefik Explicados

| Label | Propósito |
|-------|-----------|
| `traefik.enable=true` | Habilita Traefik para o serviço |
| `traefik.http.routers.*.rule` | Regra de roteamento (Host) |
| `traefik.http.routers.*.entrypoints` | EntryPoint (web/websecure) |
| `traefik.http.routers.*.tls.certresolver` | Certificado SSL |
| `traefik.http.services.*.loadbalancer.healthcheck` | Health check |
| `traefik.http.middlewares.*.ratelimit` | Rate limiting |
