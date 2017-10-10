from elasticsearch import Elasticsearch, helpers
import optparse
import requests
import json
import gzip
import os
import sys


def createIndexAndMapping():
    # Mapping Name: options.index_name
    print "Creating mapping in ES for index: %s" % (options.index_name)

    #open mappings file
    with open(options.script_dir + 'mapping.json') as f:
        mapping = json.load(f)

    """
     Let's explain what we are doing in the following section:

     Elasticsearch mappings look like this:

        {
          "<index_name>" : {
            "mappings" : {
              "<index_type>" : {
                "properties":{
                    /// all the things
                }
              }
            }
        }

     In this section, we want to build a custom mapping for each different log type
     The mapping file in ./scripts/<log-type> should be built correctly, but let's not trust this
     Need to grab the mapping file and set the index name and index type

    """

    mapping_index_name = mapping.keys()[0]                                                # name of the index in the mapping file (ie: 'elb_logs')
    mapping_index_type = mapping[mapping_index_name]['mappings'].keys()[0]                # name of the index type in the mapping file (should be the same as index name)
    properties_data = mapping[mapping_index_name]['mappings'][mapping_index_type].copy()  # this is the mapping data that we need

    mapping = {'mappings' : { options.index_type : properties_data } }                    # this is the new mapping object with the correct index name and type for this log type

    # create the index and mapping for this log type
    es.indices.create(index=options.index_name, ignore=400, body=mapping)

def putIngestPipeline():
    print 'Creating Ingest Pipeline for index: ' + options.index_name

    #open mappings file
    with open(options.script_dir + 'ingestPipeline.json') as f:
        pipeline = json.load(f)

    es.ingest.put_pipeline(id=options.index_name, body=pipeline)

def createKibanaIndexIndexPattern():
    print "Creating new index-pattern in .kibana index"

    # Create the index pattern
    url = 'http://' + options.es_host + ':5601/elasticsearch/.kibana/index-pattern/' + options.index_name
    payload = '{ "title":"' + options.index_name + '","timeFieldName":"timestamp" }'
    params_payload = { 'op_type': 'create' }
    headers = { 'kbn-version': '5.4.0' }
    r = requests.post(url, data=payload, params=params_payload, headers=headers)


    print "Setting formatted fields on index-pattern"

    #open file with objects
    with open(options.script_dir + 'kibana-index-data.json') as f:
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
    DashboardId = ""

    #open file with objects
    with open(options.script_dir + 'kibana-index-data.json') as f:
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
                DashboardId = i['_id']

    return DashboardId

def processFiles(f):
    # list for bulk documents
    documents = []

    for log_line in f:
        # Create the body and sanitize
        source = {"message": log_line.strip('\n') }
        body = {"_index": options.index_name, "_type": options.index_name, "pipeline": options.index_name, "_source": source }

        # append record to list before bulk send to ES
        documents.append(body)
        options.totalDocCount +=1

        if len(documents) >= options.bulk_limit:
            # bulk send all our entries
            status = helpers.parallel_bulk(es, documents)

            # look through each result for status
            for i in status:
                if i[0] == False:
                    print "There was an error importing a record.  Error: ", i[1]

            # Using this to have the doc count stay on one line and continually be updated
            sys.stdout.write("Total Documents sent to Elasticsearch: " + str(options.totalDocCount) + "\r")
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
        sys.stdout.write("Total Documents sent to Elasticsearch: " + str(options.totalDocCount) + "\r")
        sys.stdout.flush()

        # now clean out the document list
        documents[:] = []

    # print the final doc count before moving out of the function
    sys.stdout.write("Total Documents sent to Elasticsearch: " + str(options.totalDocCount) + "\r")

def loadFiles():
    print "Begin importing log files"

    #local vars
    failure = False

    # might be good to check if the dir they gave has files in it (valid dir)
    try:
        next(os.walk(options.log_directory))
    except:
        print ""
        print 'The directory \'' + options.log_directory + '\' doesn\'t seem to contain any log files.  Please check the --logdir argument again'
        print ""
        print "No logs imported!"
        print ""
        failure = True

    if not failure:
        # traverse root directory, and list directories as dirs and files as files
        for root, dirs, files in os.walk(options.log_directory):
            for log_file in files:
                if log_file.endswith(log_file_extension):

                    # some logs are uncompressed (*.log) and others compressed (*.gz) (and apache logs have no file extension!)
                    # Need to unpack them and send them to be processed
                    if log_file_extension == '.gz':

                        with gzip.open(root + '/' + log_file, 'rb') as f:
                            print "Importing log file: ", root + "/" + log_file
                            processFiles(f)

                    elif log_file_extension == '.log':

                        with open(root + '/' + log_file, 'rb') as f:
                            print "Importing log file: ", root + "/" + log_file
                            processFiles(f)

                    elif log_file_extension == '':

                        with open(root + '/' + log_file, 'rb') as f:
                            print "Importing log file: ", root + "/" + log_file
                            processFiles(f)

                    else:
                        # don't know how we got here, but just in case
                        # wrong file type. Will not import this log
                        print "File: " + log_file + " is not the correct format. File need to end with *" + log_file_extension

                else:
                    # wrong file type. Will not import this log
                    print "File: " + log_file + " is not the correct format. File need to end with *" + log_file_extension

        # print the final doc count before moving out of the function
        sys.stdout.write("Total Documents sent to Elasticsearch: " + str(options.totalDocCount) + "\r")



#Input Parsing
parser = optparse.OptionParser(
                                usage="""

Send AWS logs to a local dockerized Elasticsearch cluster

Required fields:
--logdir
--logtype

Valid options for log type:
elb          # ELB access logs
alb          # ALB access logs
vpc          # VPC flow logs
r53          # Route53 query logs
apache       # apache access logs\n
                                """,
                    version="0.1"
                  )

parser.add_option('-d',
                  '--logdir',
                  dest="log_directory",
                  help='directory in which the log files are located'
                  )

parser.add_option('-t',
                  '--logtype',
                  dest="logtype",
                  help='log type to import to ELK. See --help for valid options'
                  )


(options,args) = parser.parse_args()


#logdir is required
if not options.log_directory:
    parser.error('--logdir is a required field.  Use \'--help\' for a list of options')

#logtype is required
if not options.logtype:
    parser.error('--logtype is a required field.  Use \'--help\' for a list of options')

#hard setting vars that used to be cli arguments
options.es_host = 'localhost'
options.port = '9200'
options.bulk_limit = 5000

if options.logtype == 'elb':
    options.index_name = 'elb_logs'
    options.script_dir = 'scripts/elb/'
    log_file_extension = '.log'

elif options.logtype == 'alb':
    options.index_name = 'alb_logs'
    options.script_dir = 'scripts/alb/'
    log_file_extension = '.gz'

elif options.logtype == 'vpc':
    options.index_name = 'vpc_flowlogs'
    options.script_dir = 'scripts/vpc/'
    log_file_extension = '.gz'

elif options.logtype == 'r53':
    options.index_name = 'r53_query_logs'
    options.script_dir = 'scripts/r53/'
    log_file_extension = '.gz'

elif options.logtype == 'apache':
    options.index_name = 'apache_access_logs'
    options.script_dir = 'scripts/apache/'
    log_file_extension = ''

else:
    parser.error('input for --logtype is not a valid option.  Use \'--help\' for a list of options')

# although index_name is the same as index_type, we'll hard set both so the script is understandable
options.index_type = options.index_name


# var to hold total doc count sent to ES
options.totalDocCount = 0


print ""
print "Beginning import process"

#Create elasticsearch object
es = Elasticsearch(options.es_host)

# Create index and set mapping
createIndexAndMapping()

# Put the Ingest Pipeline
putIngestPipeline()

# Create a new index-pattern in .kibana index
# createKibanaIndexIndexPattern()

# Set new index-pattern to default index
# setKibanaIndexDefaultIndex()

# delete useless index-patterns in .kibana index that we will never use
# deleteKibanaIndexIndexPatterns()

# Import search / visualizations / dashboards into Kibana
# we will be returned the dashboard ID, so that we can put it in the URL at the end
# DashboardId = importObjectsToKibana()

# Load files into ES
loadFiles()


# Build the URL

url = ""

# Set the default time window to the last 24 hours.  This way people will see data in the Dashboard, since 15 minutes (the default) usually isn't enough
url_timeframe = "?_g=(refreshInterval:(display:Off,pause:!f,value:0),time:(from:now-24h,mode:quick,to:now))"

if DashboardId:
    # If DashboardId has been set, then send them directly to the dashboard URL
    url = 'http://' + options.es_host + ':5601/app/kibana#/dashboard/' + DashboardId + url_timeframe
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
