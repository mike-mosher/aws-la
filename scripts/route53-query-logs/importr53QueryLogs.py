from elasticsearch import Elasticsearch, helpers
import optparse
import requests
import gzip
import json
import os
import sys


def createIndexAndMapping():
    # Mapping Name: options.index_name
    print "Creating mapping in ES for index: %s" % (options.index_name)

    #open mappings file
    with open('r53ql-mapping.json') as f:
        elb_mapping = json.load(f)

    es.indices.create(index=options.index_name, ignore=400, body=elb_mapping['r53_query_logs'])

def putIngestPipeline():
    print 'Creating Ingest Pipeline for index: ' + options.index_name

    #open mappings file
    with open('r53ql-ingestPipeline.json') as f:
        pipeline = json.load(f)

    es.ingest.put_pipeline(id=options.index_name, body=pipeline)

def updateKibanaIndexMapping():
    # Update mappings for .kibana index
    print "Updating mapping for .kibana index"

    # pull payload from mapping file
    with open('r53ql-kibana-index-mapping.json') as f:
        mappingdata = json.load(f)

    # update search mappings
    url = 'http://' + options.es_host + ':5601/elasticsearch/.kibana/_mapping/search'
    payload = json.dumps(mappingdata['.kibana']['mappings']['search'])
    headers = { 'kbn-version': '5.4.0' }
    r = requests.put(url, data=payload, headers=headers)

    # update visualization mappings
    url = 'http://' + options.es_host + ':5601/elasticsearch/.kibana/_mapping/visualization'
    payload = json.dumps(mappingdata['.kibana']['mappings']['visualization'])
    headers = { 'kbn-version': '5.4.0' }
    r = requests.put(url, data=payload, headers=headers)

    # update dashboard mappings
    url = 'http://' + options.es_host + ':5601/elasticsearch/.kibana/_mapping/dashboard'
    payload = json.dumps(mappingdata['.kibana']['mappings']['dashboard'])
    headers = { 'kbn-version': '5.4.0' }
    r = requests.put(url, data=payload, headers=headers)

def createKibanaIndexPattern():
    print "Creating new index-pattern in .kibana index"

    # Create the index pattern
    url = 'http://' + options.es_host + ':5601/elasticsearch/.kibana/index-pattern/' + options.index_name
    payload = '{ "title":"' + options.index_name + '","timeFieldName":"dns_query_timestamp" }'
    params_payload = { 'op_type': 'create' }
    headers = { 'kbn-version': '5.4.0' }
    r = requests.post(url, data=payload, params=params_payload, headers=headers)


    print "Setting formatted fields on index-pattern"

    #open file with objects
    with open('r53ql-kibana-index-data.json') as f:
        data = json.load(f)

        for i in data['hits']['hits']:
            if i['_type'] == 'index-pattern' and i['_id'] == options.index_name:

                url = 'http://' + options.es_host + ':5601/elasticsearch/.kibana/index-pattern/' + options.index_name + '/_update'
                headers = { 'kbn-version': '5.4.0' }

                payload = { "doc": {} }
                payload['doc'].update(i['_source'])
                payload = json.dumps(payload)

                r = requests.post(url, data=payload, headers=headers)

def setKibanaIndexDefaultIndex():
    print "Setting index-pattern as default index"

    # Set the index as default
    url = 'http://' + options.es_host + ':5601/elasticsearch/.kibana/config/5.4.0/_update'
    payload = '{ "doc": { "defaultIndex": "' + options.index_name + '" } }'
    headers = { 'kbn-version': '5.4.0' }
    r = requests.post(url, data=payload, headers=headers)

def deleteKibanaIndexIndexPatterns():
    print "Deleting useless index-patterns in .kibana index"

    print "Deleting index-pattern: .ml-anomalies-*"
    # build request
    url = 'http://' + options.es_host + ':5601/elasticsearch/.kibana/index-pattern/.ml-anomalies-*'
    headers = { 'kbn-version': '5.4.0' }
    r = requests.delete(url, headers=headers)

    print "Deleting index-pattern: .ml-notifications"
    # build request
    url = 'http://' + options.es_host + ':5601/elasticsearch/.kibana/index-pattern/.ml-notifications'
    headers = { 'kbn-version': '5.4.0' }
    r = requests.delete(url, headers=headers)

def importObjectsToKibana():
    print "importing saved objects into Kibana"
    r53qlDashboardId = ""

    #open file with objects
    with open('r53ql-kibana-index-data.json') as f:
        data = json.load(f)

        for i in data['hits']['hits']:
            if i['_type'] in ['search', 'visualization', 'dashboard']:
                #Import items
                url = 'http://' + options.es_host + ':5601/elasticsearch/.kibana/' + i['_type'] + '/' + i['_id']
                payload = json.dumps(i['_source'])
                headers = { 'kbn-version': '5.4.0' }
                r = requests.post(url, data=payload, headers=headers)

            if i['_type'] == 'dashboard':
                # Need to grab the dashboard ID, so that I can create a direct link at the end
                r53qlDashboardId = i['_id']

    return r53qlDashboardId

def loadFiles():
    print "Begin importing log files"

    # list for bulk documents
    documents = []
    totDocs = 0

    # traverse root directory, and list directories as dirs and files as files
    for root, dirs, files in os.walk(options.log_directory):
        for log_file in files:
            if log_file.endswith(".gz"):
                print "Importing log file: ", root + "/" + log_file

                with gzip.open(root + '/' + log_file, 'rb') as f:
                    for log_line in f:

                        # Create the body and sanitize
                        source = {"message": log_line.replace('"', "::").strip('\n') }
                        body = {"_index": options.index_name, "_type": options.index_name, "pipeline": options.index_name, "_source": source }

                        # append record to list before bulk send to ES
                        documents.append(body)
                        totDocs +=1

                        if len(documents) >= options.bulk_limit:
                            # bulk send all our entries
                            status = helpers.parallel_bulk(es, documents)

                            # look through each result for status
                            for i in status:
                                if i[0] == False:
                                    print "There was an error importing a record.  Error: ", i[1]

                            # Using this to have the doc count stay on one line and continually be updated
                            sys.stdout.write("Total Documents sent to Elasticsearch: " + str(totDocs) + "\r")
                            sys.stdout.flush()

                            # now clean out the document list
                            documents[:] = []

                    # If we've made it here, then the file ended, and it's possible we still have documents in documents list.  Need to send what we have
                    if len(documents) > 0:
                        # bulk send all our entries
                        status = helpers.parallel_bulk(es, documents)

                        # look through each result for status
                        for i in status:
                            if i[0] == False:
                                print "There was an error importing a record.  Error: ", i[1]

                        # Using this to have the doc count stay on one line and continually be updated
                        sys.stdout.write("Total Documents sent to Elasticsearch: " + str(totDocs) + "\r")
                        sys.stdout.flush()

                        # now clean out the document list
                        documents[:] = []

            else:
                # wrong file type.  VPC flow logs should be in *.gz format
                # will not import this log
                print "File: " + log_file + " is not a Route53 query log file. Log files need to end with *.gz"

    # print the final doc count before moving out of the function
    sys.stdout.write("Total Documents sent to Elasticsearch: " + str(totDocs) + "\r")



#Input Parsing
parser = optparse.OptionParser(
                    usage="Send Route53 Query Logs to ES",
                    version="0.1"
                  )

parser.add_option('-l',
                  '--logdir',
                  dest="log_directory",
                  help='directory in which the log files are located'
                  )

parser.add_option('-i',
                  '--index',
                  dest="index_name",
                  default="r53_query_logs",
                  help="name of the index to create if not default of r53_query_logs"
                  )

parser.add_option('-s',
                  '--servername',
                  dest="es_host",
                  default="localhost",
                  help='specify an alternate ES IP address if not localhost'
                  )

parser.add_option('-p',
                  '--port',
                  dest="port",
                  default="9200",
                  help='specify an alternate ES port if not 9200'
                  )

parser.add_option('-b',
                  '--bulk',
                  dest="bulk_limit",
                  default=5000,
                  help='specify an bulk limit to batch requests to Elasticsearch'
                  )

(options,args) = parser.parse_args()

#sanitize
options.bulk_limit = int(options.bulk_limit)

# Hard-set the index name
options.index_name = "r53_query_logs"

#logdir is required
if not options.log_directory:
    parser.error('--logdir is a required field.  Use \'--help\' for a list of options')


print ""
print "Beginning import process"

#Create elasticsearch object
es = Elasticsearch(options.es_host)

# Create index and set mapping
createIndexAndMapping()

# Put the Ingest Pipeline
putIngestPipeline()

# Update .kibana index mappings
updateKibanaIndexMapping()

# Create a new index-pattern in .kibana index for elb_logs
createKibanaIndexPattern()

# Set new index-pattern to default index
setKibanaIndexDefaultIndex()

# delete useless index-patterns in .kibana index that we will never use
deleteKibanaIndexIndexPatterns()

# Import search / visualizations / dashboards into Kibana
# we will be returned the dashboard ID, so that we can put it in the URL at the end
r53qlDashboardId = importObjectsToKibana()

# Load files into ES
loadFiles()


# Build the URL

url = ""

# Set the default time window to the last 24 hours.  This way people will see data in the Dashboard, since 15 minutes (the default) usually isn't enough
url_timeframe = "?_g=(refreshInterval:(display:Off,pause:!f,value:0),time:(from:now-24h,mode:quick,to:now))"

if r53qlDashboardId:
    # If r53qlDashboardId has been set, then send them directly to the dashboard URL
    url = 'http://' + options.es_host + ':5601/app/kibana#/dashboard/' + r53qlDashboardId + url_timeframe
else:
    # I was unable to grab the dashboard ID for some reason.  Just give them the default URL
    url = 'http://' + options.es_host + ':5601/'


#Time to end this.  Give them the blurb
print ""
print "=========================================================="
print "Done!"
print "=========================================================="
print ""
print "Next Step:"
print "Browse to Kibana by opening the following link:"
print ""
print url
print ""
print "Hint: you can use cmd + double-click on the above link to open it from the terminal"
print ""
print "Dont forget to set the correct time window in the top right corner of Kibana in order to find all of your data.  The link above will show the last 24 hours of log data, but that might need to be expanded."
print ""
print "=========================================================="
print ""
