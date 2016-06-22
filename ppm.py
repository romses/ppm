#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import print_function

from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim

import atexit
import ssl
import datetime
from datetime import timedelta,date
import argparse
import socket
from tqdm import tqdm


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
#    report_prefix=str(now.strftime("%Y-%m"))
    
    (start,end)=getperiod(o)
    report_prefix=str(start.strftime("%Y-%m"))
    

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
#collect the data    

    total=len(object_view.view)
    akt=0
    

    if(o["verbose"]):
        pbar=tqdm(total=len(object_view.view))
    
    for obj in object_view.view:
        if(o["verbose"]):
            pbar.update()
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
            
    if(o["verbose"]):
        pbar.close()
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

def getperiod(o):
    now = datetime.datetime.now()
    if o["year"]==None:
        year=now.year
    else:
        year=int(o["year"])
        
    month=None
    if o["month"]!=None:
        if o["month"].upper()=="JAN" or o["month"].upper()=="JANUAR" or o["month"].upper()=="JANUARY":
            month=1
        elif o["month"].upper()=="FEB" or o["month"].upper()=="FEBRUAR" or o["month"].upper()=="FEBRUARY":
            month=2
        elif o["month"].upper()=="MAR" or o["month"].upper()=="MARCH" or o["month"].upper()=="MÄRZ":
            month=3
        elif o["month"].upper()=="APR" or o["month"].upper()=="APRIL":
            month=4        
        elif o["month"].upper()=="MAY" or o["month"].upper()=="MAI":
            month=5
        elif o["month"].upper()=="JUN" or o["month"].upper()=="JUNI":
            month=6
        elif o["month"].upper()=="JUL" or o["month"].upper()=="JULI" or o["month"].upper()=="JULY":
            month=7
        elif o["month"].upper()=="AUG" or o["month"].upper()=="AUGUST":
            month=8
        elif o["month"].upper()=="SEP" or o["month"].upper()=="SEPTEMBER":
            month=9
        elif o["month"].upper()=="OCT" or o["month"].upper()=="OKT" or o["month"].upper()=="OCTOBER" or o["month"].upper()=="OKTOBER":
            month=10
        elif o["month"].upper()=="NOV" or o["month"].upper()=="NOVEMBER":
            month=11
        elif o["month"].upper()=="DEC" or o["month"].upper()=="DEZ" or o["month"].upper()=="DECEMBER" or o["month"].upper()=="DEZEMBER":
            month=12
    if month==None:
        now = datetime.datetime.now()
        month=now.month-1
        
    if(month==0):
        month=12
        year-=1
        
    start=datetime.datetime(year,month,1,0,0)
    
    month+=1
    
    if(month==13):
        month=1
        year+=1
        
    end=datetime.datetime(year,month,1,0,0)

    return(start,end)
   
# Start program
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-m","--month", help="report month (default current month)")
    parser.add_argument("-y","--year", help="report year (default current year)")
    parser.add_argument("-v","--verbose", help="show statusbar",action="store_true")
    args = parser.parse_args()
    c=parseConfig('config.ini')
    c["month"]=args.month
    c["year"]=args.year
    c["verbose"]=args.verbose
    main(c)


