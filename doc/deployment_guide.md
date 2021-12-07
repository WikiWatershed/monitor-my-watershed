# Deployment Guide

The tech stack supporting the Data Sharing Portal has been updated and we are now deploying the application to two separate servers (one for the web application and another for the database). 

## Web Application Server

While deploying the web application server, I recommend following the instructions outlined in this guide [Digital Ocean Deployment Guide for Ubuntu 20.04](https://www.digitalocean.com/community/tutorials/how-to-set-up-django-with-postgres-nginx-and-gunicorn-on-ubuntu-20-04). However, many of the steps in the Digital Ocean guide have been modified, so additional instructions can be found below.

1. **Clone repositories:** Clone the web application and config repositories. I recommend cloning the repositories to the **'/opt'** directory using the command below.
    - `cd /opt`
    - `git clone https://github.com/ODM2/ODM2DataSharingPortal.git`
    - `git checkout develop` use 'master' branch for production server
    - `cd /opt`
    - `git clone https://github.com/LimnoTech/ODM2DataSharingPortalConfig.git`
    - `cd ./ODM2DataSharingPortalConfig`
    - `git checkout develop`
2. **Set up Python Environment:** For this project we will be using mini conda to create and manage our Python environments. I did not find a mini conda build in our package manager, so opted to get one directly from conda [Anaconda.com](https://anaconda.com). The instructions below include a link to the latest version of conda, which is what we used in our deployment. Future users of these instructions should double check available versions and consider if the latest release is correct for their application. It may make more sense to use an older LTS release for example. Also note these deployment instructions are for a server using an ARM CPU architecture. If deploying to a more traditional x86 CPU, look for the release of mini conda that is not on the 'aarch64' Linux platform.
    - `cd ~`
    - `wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-aarch64.sh`
    - `chmod +x` Miniconda-latest-Linux-aarch64.sh`
    - `sudo ./Miniconda3-latest-Linux-aarch64.sh`
        - when prompted where to install I selected '/opt/miniconda3' 
    - I also needed to add out conda install to the system path
        -`export PATH=$PATH:/opt/miniconda3/bin`
    - `conda init bash` which initializes mini conda
    - `exec bash` restart bash so that initialization takes effect 

    Next we'll set up a virtual environment from the .yml file.
    - `conda env create -f /opt/ODM2DataSharingPortal/environment_py38_dj22.yml` Note I modified this yml file so that the environment name was 'ODM2DataSharingPortal'
    - `conda activate ODM2DataSharingPortal`
3. **Create a symlink so the Web App will use the settings.json file in the config repo:** Note the instructions below use the development/staging settings. You may need to point to a different file for the production deployment.
	- `sudo ln -s /opt/ODM2DataSharingPortalConfig/django/staging.settings.json /opt/ODM2DataSharingPortal/src/WebSDL/settings/settings.json`
4. **Set Up Gunicorn:**
    - Gunicorn is not in the default mini conda channel, so we'll need to get it from conda forge.
        - `conda config --add channels conda-forge`
        - `conda install -c conda-forge gunicorn`
    - Test if guincorn starts
        - `conda activate ODM2DataSharingPortal`
        - `cd  /opt/ODM2DataSharingPortal/src`
		- `gunicorn wsgi:application --bind 0.0.0.0:8000`
    - After we know the testing works, copy over the gunicorn service file from the config repo to the server. I tried a symlink here but that did not work (probably because it is a service). I ended up just copying the file from the config repo to system services. Also note my copy command renames the file from envirodiy to gunicorn. The service we just created will automatically gunicorn with the appropriate arugments and create a socket to the application that will become the entry point for nginx. 
        - `sudo cp /opt/ODM2DataSharingPortalConfig/GUnicorn/envirodiy.service /etc/systemd/system/gunicorn.service`
    - As mentioned above, the service will automatically call gunicorn, but where gunicorn is on your system will depend on a variey of thing (i.e. how and where python was installed). In order to make the service file flexible and not dependent on the specifics of the installation I reference gunicorn located at '/usr/bin/gunicorn'. However this is very likely not were unicorn was installed. The solution is to create a symlink.
        - optional `whereis gunicorn` to help find the install location
        - `sudo ln /path/to/gunicorn /usr/bin/gunicorn`
    - Finally I needed to modify the permissions of wsgi.py so that gunicorn to spin up the application.
        - `cd /opt/ODM2DataSharingPortal/src`
        - `chmod +755 wsgi.py`
    - Now we just need to start the GUnicorn service we created
        - `sudo systemctl start gunicorn`` 
5. **Set up nginx**
	- Install nginx 
	    - `sudo apt install nginx`
    - Create symlink between config repo and nginx
        - `sudo ln -s /opt/ODM2DataSharingPortalConfig/nginx/staging_data_environdiy /etc/nginx/sites-enabled/ODM2DataSharingPortal`
    - Test nginx
        - `sudo nginx -t`
    - If there were no errors during the test, start nginx which should make the site accessable online.
        - `sudo systemctl start nginx`
        
6. **Set up SSL certificate**

  - The following commands are taken verbatim from https://certbot.eff.org/lets-encrypt/ubuntufocal-nginx.html:

    - Install current version of certbot
      - `sudo snap install core; sudo snap refresh core`
      - `sudo snap install --classic certbot`
      - `sudo ln -s /snap/bin/certbot /usr/bin/certbot`
    - Install certificate
      - `sudo certbot --nginx` (enter domain name `staging.monitormywatershed.org` when prompted)
    - Verify installation and auto-renewal
      - `sudo certbot certificates`
      - `sudo certbot renew --dry-run`

---

## Python 2.7 

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
