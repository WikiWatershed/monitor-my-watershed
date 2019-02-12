# Deployment Guide

To deploy an instance of the Data Sharing Portal, follow the [Digital Ocean Ubuntu deployment guide](https://www.digitalocean.com/community/tutorials/how-to-set-up-django-with-postgres-nginx-and-gunicorn-on-ubuntu-16-04).
This deployment guide is an outline with specific Data Sharing Portal configuration steps.

1. [Install Python 2.7](https://www.digitalocean.com/community/tutorials/how-to-set-up-django-with-postgres-nginx-and-gunicorn-on-ubuntu-16-04#install-the-packages-from-the-ubuntu-repositories) and all the packages needed from the Ubuntu Repository.
2. [Create a PostgreSQL Database and User](https://www.digitalocean.com/community/tutorials/how-to-set-up-django-with-postgres-nginx-and-gunicorn-on-ubuntu-16-04#create-the-postgresql-database-and-user) which the application will use for storing Django configuration data.
3. Create the ODM2 database for PostgreSQL with the [Database Script](https://github.com/ODM2/ODM2/blob/master/src/blank_schema_scripts/postgresql/ODM2_for_PostgreSQL.sql) provided in the [ODM2 Github Repository](https://github.com/ODM2/ODM2).
4. [Create a Python Virtual Environment](https://www.digitalocean.com/community/tutorials/how-to-set-up-django-with-postgres-nginx-and-gunicorn-on-ubuntu-16-04#create-a-python-virtual-environment-for-your-project) to install all the project requirements in an isolated Python instance. 
5. Clone the [ODM2 Data Sharing Portal](https://github.com/ODM2/ODM2DataSharingPortal.git) from our GitHub repository.
6. Start the initial django configuration by copying the file `./src/WebSDL/settings/settings_template.json` to `settings.json`, and fill out the values for each attribute with your server and database information.
7. [Complete the Initial Project Setup](https://www.digitalocean.com/community/tutorials/how-to-set-up-django-with-postgres-nginx-and-gunicorn-on-ubuntu-16-04#complete-initial-project-setup) and run these Django commands:
    - `./src/manage.py update_controlled_vocabularies`
    - `./src/manage.py set_leafpackdb_defaults`
8. [Create a Gunicorn service file](https://www.digitalocean.com/community/tutorials/how-to-set-up-django-with-postgres-nginx-and-gunicorn-on-ubuntu-16-04#create-a-gunicorn-systemd-service-file) to have a more robust way of starting and stopping the application server.
9. [Configure NGINX](https://www.digitalocean.com/community/tutorials/how-to-set-up-django-with-postgres-nginx-and-gunicorn-on-ubuntu-16-04#configure-nginx-to-proxy-pass-to-gunicorn) to pass web traffic to the Gunicorn process.

For troubleshooting, refer to the guide's [Nginx and Gunicorn troubleshooting section](https://www.digitalocean.com/community/tutorials/how-to-set-up-django-with-postgres-nginx-and-gunicorn-on-ubuntu-16-04#troubleshooting-nginx-and-gunicorn).
