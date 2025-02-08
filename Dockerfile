# Utiliser l'image officielle Node.js
FROM alpine:latest

# Installer yt-dlp
ARG build_dependencies="python3-dev"
ARG app_dependencies="py3-pip curl jq yt-dlp npm"
RUN apk add --no-cache $build_dependencies $app_dependencies

# Créer un répertoire de travail pour l'application
WORKDIR /usr/src/app

# Copier les fichiers package.json et package-lock.json pour installer les dépendances
COPY package*.json ./

# Installer les dépendances de l'application
RUN npm install

# Copier le reste des fichiers de l'application
COPY . .

# Define the volume
VOLUME [ "/downloads" ]

# Exposer le port défini par la variable d'environnement
EXPOSE ${PORT:-3000}

# Définir la commande pour démarrer l'application
CMD [ "node", "server.js" ]
