# AWS Logs to Docker ELK

## Description

These scripts allow you to easily import various AWS log types into an Elasticsearch cluster running locally on your computer in a docker container.  


## Supported AWS Log Types

 - ELB access logs
 - ALB access logs
 - VPC flow logs
 
 
## Future Log Types Supported

 - Cloudtrail audit logs
 - Cloufront access logs
 - S3 access logs
 - Apache logs (access_log / error_log)


## Steps Automated

The scripts configure everything that is needed in the ELK stack: 

 - Elasticsearch:
   - indices
   - mappings
   - ingest pipelines
   
 - Kibana:
   - index-patterns
   - field formatting for index-pattern fields
   - importing dashboards, visualizations, and dashboards
   - custom link directly to the newly created dashboard
 

## Installation Steps

 - Install [Docker for Windows][docker-for-windows] or [Docker for Mac][docker-for-mac]
 - Clone this git repository:
 
   ` git clone https://github.com/mike-mosher/AWS-Logs-to-Docker-ELK.git && cd AWS-Logs-to-Docker-ELK `

 - Install requirements:
 
   ` pip install -r ./requirements.txt `
  
 - Bring the docker environment up:
 
   ` docker-compose up -d `
  
 - Verify that the containers are running:
 
   ` docker ps `
  
 - Verify that Elasticsearch is running:
 
   ` curl -XGET localhost:9200/_cluster/health?pretty `
  
 - Move to the directory for the appropriate log type. For example, to analyze ELB access logs:
 
   ` cd scripts/elb/ `
   
 - Run the script.  The only required command line option is the folder that contains your logs:
 
   ` python importElbLogs.py -l ~/logs/elblogs/ `
  
 - Browse to the link provided in the output by using `cmd + double-click`, or browse directly to the default Kibana page:
 
   ` http://localhost:5601 `
  
 - You can import multiple log types in the same ELK cluster.  Just change to the appropriate folder and run the python script.  These logs will be kept in a separate index with separate dashboard elements:
 
   ```
    cd ..
    cd vpc-flowlogs
    python importVpcFlowLogs.py -l ~/logs/vpc-flowlogs/ 
   ```
   
 - When done, you can shutdown the containers:
 
   ` docker-compose down -v `
  

## Screenshots / Examples

 - Dashboard that is imported to the ELK cluster when importing ALB Access Logs:
 
[ALB Dashboard](screenshots/ALB Dashboard Screenshots/ALB Dashboard.jpg?raw=true)
 
 
 
 

 

[docker-for-windows]: https://docs.docker.com/docker-for-windows/install/#download-docker-for-windows
[docker-for-mac]: https://docs.docker.com/docker-for-mac/install/#download-docker-for-mac
