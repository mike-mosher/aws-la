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
  

## Screenshots / Examples:

 - Python output:
 ![Python script output][cli-output]
   - As you can see, I was able to import 12.5 million VPC flowlogs in around 2 hours
 
 - Searching for traffic initiated by RFC1918 (private) IP addresses:
   - Browse to Discover tab, and enter the following query in the query bar:
   
   ` source_ip_address:"10.0.0.0/8" OR source_ip_address:"172.16.0.0/12" OR source_ip_address:"192.168.0.0/16" `
   
   ![Search for RFC1918 Traffic][search-rfc1918]
   
  - Alternately, you can search for all traffic initiated by Public IP addresses in the logs:
  
  ` NOT (source_ip_address:"10.0.0.0/8" OR source_ip_address:"172.16.0.0/12" OR source_ip_address:"192.168.0.0/16") `
  
  ![Search for non-RFC1918 Traffic][search-non-rfc1918]
  
  - Search for a specific flow to/from a specific ENI:
  
  ` interface-id:<eni-name> AND (source_port:<port> OR dest_port:<port>) `
  
  ![Search flow to Specific ENI][search-eni]
    - Note: VPC Flow Logs split a flow into two log entries, so the above search will find both sides of the flow and show packets / bytes for each
 
 - Dashboard imported for VPC Flow Logs:
 ![VPC Dashboard][vpc-dashboard]
 
 - Dashboard imported for ALB Access Logs:
 ![ALB Dashboard][alb-dashboard]
 
 
 
 

 

[docker-for-windows]: https://docs.docker.com/docker-for-windows/install/#download-docker-for-windows
[docker-for-mac]: https://docs.docker.com/docker-for-mac/install/#download-docker-for-mac
[cli-output]: screenshots/VFL_example_12.5m_documents_imported.png?raw=true
[alb-dashboard]: screenshots/ALB_Dashboard_Screenshots/ALB_Dashboard.jpg?raw=true
[vpc-dashboard]: screenshots/VPC_Dashboard_Screenshots/VPC_Flow_Logs_Dashboard.jpg?raw=true
[search-rfc1918]: screenshots/VPC_Dashboard_Screenshots/Search_for_RFC1918_traffic.png?raw=true
[search-non-rfc1918]: screenshots/VPC_Dashboard_Screenshots/Search_for_non_RFC1918_traffic.png?raw=true
[search-eni]: screenshots/VPC_Dashboard_Screenshots/Search_for_both_sides_of_a_flow_record_for_a_specific_ENI.png?raw=true
