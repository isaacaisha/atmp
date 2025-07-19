# atmp commands eg.:

python manage.py collectstatic
sudo systemctl daemon-reload
sudo systemctl restart atmp.service
sudo systemctl status atmp.service

sudo nginx -t
sudo systemctl restart nginx
sudo systemctl status nginx

python manage.py makemigrations
python manage.py migrate

sudo journalctl -u atmp.service -f

source venv/bin/activate
export DATABASE_URL=postgresql://postgres:Toure7Medina@localhost:5432/atmp_db
python manage.py runserver 0.0.0.0:8079

# CONNECT POSTGRES
sudo -i -u postgres
sudo nano /var/lib/pgsql/data/postgresql.conf

# systemd
sudo nano /etc/systemd/system/atmp.service

# nginx
sudo nano /etc/nginx/sites-available/atmp.conf

# CREATE SSL CERTIFICATE
sudo dnf install certbot python-certbot-nginx
sudo certbot --nginx

# link the configuration to enable it
sudo ln -s /etc/nginx/sites-available/atmp.conf /etc/nginx/sites-enabled/

sudo certbot certificates
sudo certbot --nginx -d atmp.siisi.online -d www.atmp.siisi.online

sudo openssl dhparam -out /etc/ssl/certs/dhparam.pem 2048

sudo systemctl enable certbot.timer
sudo certbot renew --dry-run

# kill all port runing
sudo lsof -t -iTCP:8001 -sTCP:LISTEN | xargs sudo kill

# Find Your Computer's Local IP Address
ifconfig | grep inet

# Testing
python -m gunicorn --workers 3 --bind unix:/home/siisi/atmp/atmp.sock siisi.wsgi:application

## Docker
# Start services

# Start DB + Django runserver
# Rebuild static assets & restart
<!-- prod -->
docker compose -f docker-compose.prod.yml -p atmp_prod run atmp python manage.py collectstatic
<!-- Collect static files INSIDE the container -->
docker compose -f docker-compose.prod.yml -p atmp_prod run --rm atmp \
  python manage.py collectstatic --noinput

docker-compose -f docker-compose.prod.yml -p atmp_prod down --volumes --remove-orphans
docker system prune -a --volumes
docker-compose -f docker-compose.prod.yml -p atmp_prod down -v
docker-compose -f docker-compose.prod.yml -p atmp_prod up -d --build --remove-orphans
docker-compose -f docker-compose.prod.yml -p atmp_prod ps
docker-compose -f docker-compose.prod.yml -p atmp_prod down
docker-compose -f docker-compose.prod.yml -p atmp_prod up -d --remove-orphans --build
docker-compose -f docker-compose.prod.yml -p atmp_prod logs -f nginx
docker-compose -f docker-compose.prod.yml -p atmp_prod logs -f

<!-- dev -->
docker compose -f docker-compose.dev.yml -p atmp_dev run atmp python manage.py collectstatic
docker-compose -f docker-compose.dev.yml down --volumes --remove-orphans
docker system prune -a --volumes
docker-compose -f docker-compose.dev.yml -p atmp_dev down -v
docker-compose -f docker-compose.dev.yml -p atmp_dev up -d --remove-orphans --build
docker-compose -f docker-compose.dev.yml -p atmp_dev ps
docker-compose -f docker-compose.dev.yml -p atmp_dev down
docker-compose -f docker-compose.dev.yml -p atmp_dev up -d --remove-orphans --build
docker-compose -f docker-compose.dev.yml -p atmp_dev logs -f nginx
docker-compose -f docker-compose.dev.yml -p atmp_dev logs -f

# Apply migrations or create superuser
<!-- prod -->
docker exec -it atmp_prod-atmp-1 python manage.py makemigrations
docker exec -it atmp_prod-atmp-1 python manage.py migrate
docker exec -it atmp_prod-atmp-1 python manage.py createsuperuser
docker exec -it atmp_prod-atmp-1 python manage.py shell
docker exec -it atmp_prod-atmp-1 bash

<!-- dev -->
docker exec -it atmp_dev-atmp-1 python manage.py makemigrations
docker exec -it atmp_dev-atmp-1 python manage.py migrate
docker exec -it atmp_dev-atmp-1 python manage.py createsuperuser
docker exec -it atmp_dev-atmp-1 python manage.py shell
docker exec -it atmp_dev-atmp-1 bash

# ex. create a folder and set the permission
mkdir -p media/profile_img
# Change owner to siisi:siisi
sudo chown -R siisi:siisi media/profile_img
# Give user and group write permissions, others only read/execute
chmod -R 755 media/profile_img

# Siret: 918 881 913 00019


# For a New DossierATMP
{
  "created_by": 9,
  "safety_manager": 8,
  "title": "Chute dans l’atelier de peinture",
  "description": "L’employé a glissé sur une flaque d’huile près de la cabine de peinture.",
  "date_of_incident": "2025-07-18",
  "location": "Usine de peinture, Quai 4, Zone industrielle",
  "status": "A_ANALYSER",
  "entreprise": {
    "nom": "Peintures & Co",
    "adresse": "12 rue des Arts, 75005 Paris",
    "siret": "123 456 789 00010"
  },
  "salarie": {
    "nom": "Dupont",
    "prenom": "Jean",
    "matricule": "EMP-0456",
    "poste": "Opérateur cabine"
  },
  "accident": {
    "type": "Glissade",
    "gravite": "Mineure",
    "description_details": "Talon glissé sur une tâche d’huile non signalée."
  },
  "temoins": [
    {
      "nom": "Martin",
      "prenom": "Julie",
      "contact": "julie.martin@example.com"
    }
  ],
  "tiers_implique": [
    {
      "nom": "Fournisseur PeintureX",
      "role": "Intervenant externe"
    }
  ],
  "service_sante": "Clinique du Travail, Dr. Lambert",
  "documents": []
}


# For a New Contentieux Record
{
  "dossier_atmp": 1,
  "reference": "CONT-1626742800",
  "subject": {
    "objet": "Contestation de la décision CPAM"
  },
  "juridiction_steps": {
    "etape1": "Cour d'appel",
    "etape2": "Cour de cassation"
  },
  "status": "DRAFT",
  "documents": [],
  "actions": []
}


# For a New Audit Record
{
  "dossier_atmp": 1,
  "auditor": 2,
  "checklist": ["item A"],
  "status": "NOT_STARTED",
  "decision": "DO_NOT_CONTEST",
  "comments": "Kickoff audit today."
}
