# Examen Transversal - INY1105 Infraestructura de Aplicaciones I

**Nombre:** Cristóbal Sarmiento

---

## 1. Justificacion tecnica

### 1.1 Contenedores vs. hipervisores (virtualizacion tradicional)

| Aspecto | Hipervisores (VMs) | Contenedores (Docker) |
|---|---|---|
| Arquitectura | Cada VM incluye un sistema operativo completo sobre un hipervisor (Tipo 1: VMware ESXi, Hyper-V; Tipo 2: VirtualBox). | Los contenedores comparten el kernel del host y solo empaquetan la aplicacion y sus dependencias. |
| Consumo de recursos | Alto: cada VM requiere CPU, RAM y disco dedicados para su SO completo. | Bajo: sin SO adicional, arranque en segundos, menor uso de RAM y disco. |
| Tiempo de despliegue | Minutos a horas (instalar SO, configurar servicios). | Segundos (descargar imagen y ejecutar contenedor). |
| Portabilidad | Limitada al hipervisor y formato de imagen (VMDK, VHD, OVA). | Alta: la misma imagen corre en cualquier host con Docker instalado (Linux, Windows, macOS, nube). |
| Licenciamiento | Requiere licencias del hipervisor (VMware vSphere, Hyper-V Server) y de cada SO guest (Windows Server, RHEL). Costos elevados. | Docker Engine es open source (Apache 2.0). Las imagenes base como python:3-slim y nginx:stable son gratuitas. Solo Docker Desktop comercial tiene licencia paga para empresas grandes. |
| Escalabilidad | Escalar implica crear nuevas VMs completas, proceso lento y costoso en recursos. | Escalar implica levantar nuevos contenedores en segundos con Docker Compose o un orquestador. |
| Aislamiento | Fuerte: cada VM tiene su propio kernel. | Buen aislamiento a nivel de proceso mediante namespaces y cgroups, aunque comparten el kernel del host. |

Para el caso de VZeta, la solucion basada en contenedores Docker es la opcion correcta porque el stack consta de tres servicios ligeros (NGINX, Flask, PostgreSQL) que no justifican el costo de tres maquinas virtuales completas. Docker permite empaquetar cada servicio en una imagen reproducible, desplegar todo el stack en segundos con Docker Compose y mantener un entorno identico entre desarrollo y produccion. Ademas, la restriccion del caso indica que no se permite orquestacion avanzada (Kubernetes/EKS), por lo que Docker Compose sobre una instancia EC2 es la herramienta adecuada.

### 1.2 Propuesta de nube: publica, privada e hibrida

| Tipo de nube | Descripcion | Ventajas | Desventajas |
|---|---|---|---|
| Publica (AWS, Azure, GCP) | Infraestructura de terceros compartida, accesible por internet. | Sin inversion inicial en hardware, pago por uso, escalabilidad inmediata, alta disponibilidad global. | Menor control sobre la infraestructura fisica, costos variables que pueden crecer, dependencia del proveedor (vendor lock-in). |
| Privada (on-premise o dedicada) | Infraestructura exclusiva de la organizacion, en su propio datacenter o en hosting dedicado. | Control total sobre hardware y seguridad, cumplimiento normativo mas sencillo, latencia predecible. | Alta inversion inicial (CAPEX), requiere personal para mantenimiento, escalabilidad limitada y lenta. |
| Hibrida | Combina nube publica y privada, permitiendo mover cargas de trabajo entre ambas. | Flexibilidad: datos sensibles en nube privada, cargas variables en nube publica. Optimiza costos y cumplimiento. | Mayor complejidad de gestion, requiere integracion entre ambos entornos y personal capacitado. |

**Propuesta para VZeta:** Se recomienda nube publica (AWS) para este despliegue. La empresa necesita agilidad y bajo costo inicial; AWS ofrece instancias EC2 que se aprovisionan en minutos y se pagan por uso. Docker sobre EC2 permite desplegar el stack completo sin necesidad de infraestructura propia. Si en el futuro VZeta maneja datos sensibles o regulados, podria migrar a un modelo hibrido, manteniendo la aplicacion en nube publica y la base de datos en infraestructura privada. Para este examen se utiliza AWS Learner Lab en la region us-east-1.

---

## 2. Descripcion de la arquitectura

El stack se compone de tres contenedores orquestados con Docker Compose sobre una instancia EC2 de AWS:

```
Cliente -- HTTP:80 --> [ mynginx_container ] --> [ myapp_container ] --> [ db_container ]
                       (NGINX reverse proxy)    (Flask, imagen propia)  (PostgreSQL + volumen pgdata)
```

- **mynginx_container**: NGINX actua como reverse proxy. Escucha en el puerto 80 del host y redirige las peticiones HTTP hacia myapp en el puerto 5000 interno.
- **myapp_container**: Aplicacion web Python/Flask construida con imagen propia (FROM python:3-slim). Al recibir una peticion en "/", se conecta a PostgreSQL, registra la visita y muestra el contador.
- **db_container**: PostgreSQL 15 con un volumen Docker (pgdata) montado en /var/lib/postgresql/data para persistencia de datos.
- **Red**: Los tres contenedores se comunican a traves de una red bridge llamada vzeta_network.
- **Volumen**: pgdata asegura que los datos de la base de datos persistan al detener o eliminar los contenedores.

### Estructura de archivos

```
repo/
 ├── app/
 │    ├── app.py               # Aplicacion Flask (contador de visitas)
 │    └── requirements.txt     # Dependencias Python (flask, psycopg2-binary)
 ├── nginx/
 │    └── default.conf         # Configuracion del reverse proxy
 ├── Dockerfile                # Imagen propia de myapp (FROM python:3-slim)
 ├── docker-compose.yml        # Orquestacion de los tres servicios
 ├── evidencias/               # Capturas de pantalla
 └── README.md                 # Este archivo
```

---

## 3. Procedimiento de despliegue paso a paso

### 3.1 Crear la instancia EC2 en AWS Learner Lab

1. Iniciar el laboratorio en AWS Academy y abrir la consola AWS.
2. Ir a EC2 > Launch Instance.
3. Configurar: nombre "vzeta-docker", Amazon Linux 2023 o Ubuntu 22.04, tipo t2.small, key pair "vockey", security group con puertos 22 (SSH) y 80 (HTTP) abiertos.
4. Lanzar la instancia y conectarse por SSH.

### 3.2 Instalar Docker Engine y Docker Compose

```bash
sudo yum update -y
sudo yum install -y docker
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker ec2-user
```

Cerrar y volver a abrir la sesion SSH para que el grupo docker se aplique, luego:

```bash
docker --version
```

Instalar el plugin Docker Compose:

```bash
sudo mkdir -p /usr/local/lib/docker/cli-plugins
sudo curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 -o /usr/local/lib/docker/cli-plugins/docker-compose
sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
docker compose version
```

### 3.3 Clonar el repositorio y construir

```bash
git clone https://github.com/TU_USUARIO/TU_REPOSITORIO.git
cd TU_REPOSITORIO
```

Construir la imagen de myapp:

```bash
docker build -t myapp:latest .
```

### 3.4 Levantar el stack con Docker Compose

```bash
docker compose up -d
```

### 3.5 Verificar funcionamiento

```bash
docker ps
curl http://localhost/
curl http://localhost/
curl http://localhost/
```

El contador debe incrementarse con cada peticion.

### 3.6 Comprobar persistencia

```bash
docker compose down
docker compose up -d
curl http://localhost/
```

El contador debe mantener el valor anterior y seguir sumando.

---

## 4. Evidencias

### 4.1 Instancia EC2 creada

![Instancia EC2 creada en AWS](evidencias/01-instancia-ec2.png)

### 4.2 Docker Engine instalado

![Docker version instalada](evidencias/02-docker-version.png)

### 4.3 Docker Compose instalado

![Docker Compose version](evidencias/03-docker-compose-version.png)

### 4.4 Imagen propia construida (docker build)

![Imagen construida con docker build](evidencias/04-docker-build.png)

### 4.5 Imagenes Docker disponibles

![Listado de imagenes con docker images](evidencias/05-docker-images.png)

### 4.6 Stack levantado con docker compose up -d

![Stack levantado con docker compose](evidencias/06-docker-compose-up.png)

### 4.7 Contenedores en ejecucion (docker ps)

![Contenedores corriendo](evidencias/07-docker-ps.png)

### 4.8 Aplicacion funcionando (curl)

![Resultado de curl mostrando el contador](evidencias/08-curl-funcionando.png)

### 4.9 Aplicacion funcionando en navegador

![Aplicacion en el navegador con IP publica](evidencias/09-navegador.png)

### 4.10 Persistencia de datos (docker compose down y up)

![Persistencia del contador tras reinicio del stack](evidencias/10-persistencia.png)

### 4.11 Volumen Docker (docker volume ls e inspect)

![Volumen pgdata listado](evidencias/11-volumen.png)

### 4.12 Docker inspect - Mounts del contenedor db

![Inspect Mounts de db_container](evidencias/12-inspect-mounts.png)

### 4.13 Docker inspect - Red vzeta_network

![Inspect de la red vzeta_network](evidencias/13-inspect-red.png)

### 4.14 Docker inspect - Contenedor myapp

![Inspect del contenedor myapp_container](evidencias/14-inspect-myapp.png)

### 4.15 Docker logs

![Logs del contenedor myapp](evidencias/15-docker-logs.png)

### 4.16 Docker stats

![Estadisticas de los contenedores](evidencias/16-docker-stats.png)

### 4.17 Docker restart

![Reinicio de contenedor](evidencias/17-docker-restart.png)

### 4.18 Docker stop

![Detencion de contenedor](evidencias/18-docker-stop.png)

### 4.19 Docker rename

![Renombrado de contenedor](evidencias/19-docker-rename.png)

### 4.20 Docker rm y rmi

![Eliminacion de contenedor e imagen](evidencias/20-docker-rm-rmi.png)

### 4.21 Stack restaurado final

![Stack operativo tras docker compose up -d final](evidencias/21-stack-final.png)
