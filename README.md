# AWS-LA (AWS Log Analyzer)

## Description

These scripts allow you to easily import various AWS log types into an Elasticsearch cluster running locally on your computer in a docker container.

## Supported AWS Log Types

- ELB access logs
- ALB access logs
- VPC flow logs
- [Route53 Query Logs][r53-query-logs]

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

  `git clone https://github.com/mike-mosher/AWS-Logs-to-Docker-ELK.git && cd AWS-Logs-to-Docker-ELK`

- Install requirements:

  `pip install -r ./requirements.txt`

## Running the Script

- Bring the docker environment up:

  `docker-compose up -d`

- Verify that the containers are running:

  `docker ps`

- Verify that Elasticsearch is running:

  `curl -XGET localhost:9200/_cluster/health?pretty`

- To run the script, specify the log type and directory containing the logs. For example, you could run the following command to import ELB Access Logs

  `python importLogs.py --logtype elb --logdir ~/logs/elblogs/`

- Valid log types are specified by running the `--help` argument. Currently, the valid logtypes are the following:

  ```
  --logtype elb
  --logtype alb
  --logtype vpc
  --logtype r53
  ```

- Browse to the link provided in the output by using `cmd + double-click`, or browse directly to the default Kibana page:

  `http://localhost:5601`

- You can import multiple log types in the same ELK cluster. Just run the command again with the new log type and log directory:

  ```
   python importVpcFlowLogs.py --logtype vpc --logdir ~/logs/vpc-flowlogs/
  ```

- When done, you can shutdown the containers:

  `docker-compose down -v`

## Screenshots / Examples:

- Python output: ![Python script output][cli-output]

  - As you can see, I was able to import 12.5 million VPC flowlogs in around 2 hours

- Searching for traffic initiated by RFC1918 (private) IP addresses:

  - Browse to Discover tab, and enter the following query in the query bar:

  `source_ip_address:"10.0.0.0/8" OR source_ip_address:"172.16.0.0/12" OR source_ip_address:"192.168.0.0/16"`

  ![Search for RFC1918 Traffic][search-rfc1918]

  - Alternately, you can search for all traffic initiated by Public IP addresses in the logs:

  `NOT (source_ip_address:"10.0.0.0/8" OR source_ip_address:"172.16.0.0/12" OR source_ip_address:"192.168.0.0/16")`

  ![Search for non-RFC1918 Traffic][search-non-rfc1918]

  - Search for a specific flow to/from a specific ENI:

  `interface-id:<eni-name> AND (source_port:<port> OR dest_port:<port>)`

  ![Search flow to Specific ENI][search-eni]

  - Note: VPC Flow Logs split a flow into two log entries, so the above search will find both sides of the flow and show packets / bytes for each

- Dashboard imported for VPC Flow Logs: ![VPC Dashboard][vpc-dashboard]

- Dashboard imported for ALB Access Logs: ![ALB Dashboard][alb-dashboard]

[alb-dashboard]: examples_screenshots/ALB_Dashboard_Screenshots/ALB_Dashboard.jpg?raw=true
[cli-output]: examples_screenshots/VFL_example_12.5m_documents_imported.png?raw=true
[docker-for-mac]: https://docs.docker.com/docker-for-mac/install/#download-docker-for-mac
[docker-for-windows]: https://docs.docker.com/docker-for-windows/install/#download-docker-for-windows
[r53-query-logs]: https://aws.amazon.com/about-aws/whats-new/2017/09/amazon-route-53-announces-support-for-dns-query-logging/
[search-eni]: examples_screenshots/VPC_Dashboard_Screenshots/Search_for_both_sides_of_a_flow_record_for_a_specific_ENI.png?raw=true
[search-non-rfc1918]: examples_screenshots/VPC_Dashboard_Screenshots/Search_for_non_RFC1918_traffic.png?raw=true
[search-rfc1918]: examples_screenshots/VPC_Dashboard_Screenshots/Search_for_RFC1918_traffic.png?raw=true
[vpc-dashboard]: examples_screenshots/VPC_Dashboard_Screenshots/VPC_Flow_Logs_Dashboard.jpg?raw=true
