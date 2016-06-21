#!/usr/bin/python

from __future__ import print_function

from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim

import atexit
import ssl
import datetime
from datetime import timedelta,date


def main(o):
# accept any certificate here
    context=0
    if hasattr(ssl, 'SSLContext'):
        context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
        context.verify_mode = ssl.CERT_NONE
    try:
        if context:
            si = SmartConnect(host=o["esxserver"],user=o["username"],pwd=o["password"],port=443,sslContext=context)
        else:
            si = SmartConnect(host=o["esxserver"],user=o["username"],pwd=o["password"],port=443)
    except socket.gaierror as e:
        print("cannot connect to "+o["esxserver"])
        return -3
    except Exception as e:
        print("connection error")
        print(type(e))
        return -2
        
    if not si:
        print("Could not connect to the specified host using specified "
              "username and password")
        return -1

    atexit.register(Disconnect, si)
    
    content = si.RetrieveContent()
#prepare the report date range
    now = datetime.datetime.now()
    report_prefix=str(now.strftime("%Y-%m"))

    if (now.month-1)==0:
        start=datetime.datetime(now.year-1,12,1,0,0)
    else:
        start=datetime.datetime(now.year,(now.month-1),1,0,0)

    end=datetime.datetime(now.year,now.month,1,0,0)

#Gather Host,vm and datastore Data
    object_view = content.viewManager.CreateContainerView(content.rootFolder,[vim.VirtualMachine,vim.HostSystem,vim.Datastore], True)
#open the report files    
    fvm = open(report_prefix+"-vm-report.csv","w")
    fhost = open(report_prefix+"-host-report.csv","w")
    fdatastore = open(report_prefix+"-datastore-report.csv","w")
#print the report headers in CSV    
    printHeader(start,end,fvm)
    printHeader(start,end,fhost)
    fdatastore.write("Datastore, Used (GB), Free (GB), Total (GB)\n")
#collect teh data    
    for obj in object_view.view:
        if isinstance(obj,vim.VirtualMachine) or isinstance(obj,vim.HostSystem):
            content = si.RetrieveContent()
            search_index = content.searchIndex
            perfManager = content.perfManager
#counterID=6 -> collect CPU/MHz        
            metricId = vim.PerformanceManager.MetricId(counterId=6, instance="*")
#execute the query
            query = vim.PerformanceManager.QuerySpec(maxSample=60, entity=obj,
                                                 metricId=[metricId],
                                                 startTime=start, endTime=end)

            res=perfManager.QueryPerf(querySpec=[query])
#save the data	  
        if isinstance(obj, vim.VirtualMachine):
            printData(obj.name,res,start,end,fvm)
        if isinstance(obj, vim.HostSystem):
            printData(obj.name,res,start,end,fhost)
        if isinstance(obj, vim.Datastore):
            if(obj.info.vmfs.local==False):                             # Skip all local datastores
                fdatastore.write("{}, {}, {}, {}\n".format(obj.summary.name,
                                             sizeof_fmt(obj.summary.capacity-obj.summary.freeSpace),
                                             sizeof_fmt(obj.summary.freeSpace),
                                             sizeof_fmt(obj.summary.capacity)))         
            
    fvm.close()
    fhost.close()
    fdatastore.close()    
    
def sizeof_fmt(num):
    return "%3.1f" % (num/(1024*1024*1024.0))
    
def printData(name,res,start,end,f):
    if res:
        if res[0].sampleInfo:
            f.write(name+",")
            accumulated=0
            for d in daterange(start,end):
                present=1

                for i in range(0,len(res[0].sampleInfo)-1):
                    if d==res[0].sampleInfo[i].timestamp.replace(tzinfo=None):
                        f.write(str(float(res[0].value[0].value[i])/100)+" ,")
                        accumulated+=float(res[0].value[0].value[i])/100
                        present=0
                if present!=0:
                    f.write("0,")
            f.write(","+str(accumulated)+"\n")

def printHeader(start,end,f):
    f.write(" ,")
    for d in daterange(start,end):
        f.write(str(d)+",")
    f.write(",accumulated\n")

#iterator for date ranges    
def daterange(start_date, end_date):
   for n in range(int ((end_date - start_date).days)):
      yield start_date + timedelta(n)
		 
#simple config parser         
def parseConfig(filename):
   COMMENT_CHAR = '#'
   OPTION_CHAR =  '='
   options = {}
   f = open(filename)
   for line in f:
      if COMMENT_CHAR in line:
         line, comment = line.split(COMMENT_CHAR, 1)
      if OPTION_CHAR in line:
         option, value = line.split(OPTION_CHAR, 1)
         option = option.strip()
         value = value.strip()
         options[option] = value
   f.close()

   return options

# Start program
if __name__ == "__main__":
   main(parseConfig('config.ini'))


