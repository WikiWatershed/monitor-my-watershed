# ODM2DataSharingPortal
This repository contains the code for a Python-Django web application enabling users to upload, share, and display data from their environmental monitoring sites. Data can either be automatically streamed from Internet of Things (IoT) devices, manually uploaded via CSV files, or manually entered into forms.

The ODM2 Data Sharing Portal is built on the [Observations Data Model Version 2 (ODM2)](http://www.odm2.org) information model and supporting software ecosystem, includuing an ODM2 database instance in PostgreSQL for data storage in the backend. Any environmental IoT device or computer can upload data to the web app via HTTP POST. Complete documentation is available in our open-access journal article ["Low-Cost, Open-Source, and Low-Power: But What to Do With the Data?"](https://doi.org/10.3389/feart.2019.00067).

![Data Sharing Portal Architecture](https://github.com/ODM2/ODM2DataSharingPortal/blob/master/doc/ArchitectureDiagram/Data%20Sharing%20Portal%20Architecture%20with%20Logos%20-%20Copy.png)

The ODM2 Data Sharing Portal was initially designed to support the [EnviroDIY community](http://www.envirodiy.org) for do-it-yourself environmental science and monitoring and their network of open-source monitoring stations built with Arduino-framework dataloggers such as the [EnviroDIY Mayfly Datalogger](https://github.com/EnviroDIY/EnviroDIY_Mayfly_Logger).

The ODM2 Data Sharing Portal was extended to also support the [Leaf Pack Network](https://leafpacknetwork.org) of teachers, students, and citizen monitors who assess aquatic ecosystem health through aquatic macroinvertebrate surveys using [Leaf Pack Experiment](https://leafpacknetwork.org/resources/equipment/) stream ecology kits.

The main instance of this application is currently hosted at http://monitormywatershed.org.

## Deployment Guide
A guide for deploying the data sharing portal is available [here](https://github.com/ODM2/ODM2DataSharingPortal/blob/master/doc/deployment_guide.md).

## Example POST Requests for Streaming Data
The ODM2DataSharingPortal relies on devices that can push data to the web using HTTP POST requests. We've included some documentation where you can view [example POST requests](https://github.com/ODM2/ODM2WebSDL/blob/master/doc/example_rest_requests.md) to learn the syntax.

## EnviroDIY Datalogger Code and Libraries
The source code for the EnviroDIY Mayfly loggers, examples, and libraries are hosted in GitHub at https://github.com/EnviroDIY.

## Credits
Funding for this work was provided by the William Penn Foundation under grant 158-15.

The authors gratefully acknowledge the work and contributions of the EnviroDIY community and those who participated in testing and advancing the Monitor My Watershed Data Sharing Portal software.
