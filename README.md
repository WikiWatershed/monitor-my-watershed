# ODM2DataSharingPortal
This repository contains the code for a web-based application that enables upload and display of data from environmental monitoring sites. Data can be manually uploaded via a file or streamed from web-enabled, environmental data collection devices. The application uses an Observations Data Model Version 2 (ODM2) database instance for data storage in the backend. For streaming data, any web-enabled device or computer can POST data to an instance of this application, but we have primarily designed it for data collected by citizen scientists using Arduino-based Mayfly dataloggers in collaboration with the EnviroDIY community. Learn more at http://www.envirodiy.org.

The main instance of this application is currently hosted at http://monitormywatershed.org.

## Deployment Guide
A guide for deploying the data sharing portal is available [here](https://github.com/ODM2/ODM2DataSharingPortal/blob/master/doc/deployment_guide.md).

## Example POST Requests for Streaming Data
The ODM2DataSharingPortal relies on devices that can push data to the web using HTTP POST requests. We've included some documentation where you can view [example POST requests](https://github.com/ODM2/ODM2WebSDL/blob/master/doc/example_rest_requests.md) to learn the syntax.

## EnviroDIY Datalogger Code and Libraries
The source code for the EnviroDIY Mayfly loggers, examples, and libraries are hosted in GitHub at https://github.com/EnviroDIY.

## Credits 
Funding for this work was provided by the William Penn Foundation under grant 158-15. Any opinions expressed herein are those of the authors and do not necessarily reflect the views of the William Penn Foundation. The authors gratefully acknowledge the work and contributions of the EnviroDIY community and those who participated in testing and advancing the Monitor My Watershed Data Sharing Portal software.
