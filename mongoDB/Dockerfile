# Use the official MongoDB image as the base image
FROM mongo:latest

# Set environment variables
#ENV MONGO_INITDB_ROOT_USERNAME=admin
#ENV MONGO_INITDB_ROOT_PASSWORD=adminpassword
#ENV MONGO_INITDB_DATABASE=mydatabase

# Copy initialization scripts to the container
COPY ./mongo-init.js /docker-entrypoint-initdb.d/

# Expose MongoDB default port
EXPOSE 27017

# (Optional) Set a volume for persisting data outside the container
VOLUME /data/db

# (Optional) Set the working directory
WORKDIR /usr/src/app
