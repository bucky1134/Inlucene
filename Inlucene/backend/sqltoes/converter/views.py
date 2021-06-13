from django.shortcuts import render
import sqlparse
from sqlparse import sql
import json
from json2html import *
import re
import pandas as pd
import requests
from operator import itemgetter
from config import *
def elasticToDataframe(elasticResult,aggStructure,record={},fulllist=[]):
    for agg in aggStructure:
        buckets = elasticResult[agg['key']]['buckets']
        for bucket in buckets:
            record = record.copy()
            record[agg['key']] = bucket['key']
            if 'aggs' in agg: 
                elasticToDataframe(bucket,agg['aggs'],record,fulllist)
            else: 
                for var in agg['variables']:
                    record[var['dfName']] = bucket[var['elasticName']]

                fulllist.append(record)
    df = pd.DataFrame(fulllist)
    return df
class queryconverter:
    def __init__(self):
        self.search_query = {
            "size":5000,
                "query": {
                    "bool": {

                        }
                    },
                "_source": {
                    "includes": [
                            ],
                    "excludes": []
                    }
                }
        self.aggregation_value=''
        self.aggregation_flag=False
        self.grouplist=''
        self.glist=''
                

    def getmustclause(self):
        try:
            self.search_query['query']['bool']['must']
        except KeyError:
            present = False
        else:
            present = True
        return present


    def getshouldclause(self):
        try:
            self.search_query['query']['bool']['should']
        except KeyError:
            present = False
        else:
            present = True
        return present
    
    def get_groupbyclause(self,value):
        group_list=()
        group_list=str(value).split(',')
        self.glist=group_list
        self.grouplist=reversed(group_list)
        return

    def _comparison(self,key):
        tempdict = {'match': {key.left.value:{}}}
        tempdict['match'][key.left.value]['query'] = key.right.value.replace("'", '')
        tempdict['match'][key.left.value]['type'] ='phrase'
        return tempdict

    def getinnervalue(self,value):
        valuelist = []
        valuelist = value.split(',')
        try:
            for i in valuelist:
                if i.upper().startswith('COUNT('):
                    self.search_query['size']='0'
                    self.aggregation_flag=True
                    result=re.search(r"\(([A-Za-z0-9_*]+)\)", i).group(1)
                    if result=='*':
                        self.aggregation_value='_index'
                    else:
                        self.aggregation_value=result+'.keyword'
                    temp = {i:{'value_count':{}}}
                    temp[i]['value_count']['field']=self.aggregation_value
                    self.search_query['aggregations']=temp
                    valuelist.remove(i)   
                    valuelist.append('COUNT') 
        except Exception as e:
                print(e)
        return valuelist

    def getparenthesis(self,key, identifier, prevclause):
        tempdict = {'terms': {}}
        if identifier != '':
            newlist = []
            newlist = str(key).replace('(', '').replace(')',
                                                        '').replace("'", '').split(',')
            
            tempdict['terms'][identifier] = newlist
            return tempdict
        else:
            return {}
def index(request):
    return render(request,'pages/index.html')

def convert(request):
    if request.method=='POST':
        try:
            query=str(request.POST['sqlquery'])
            if query!='':
                obj=queryconverter()
                parsed = sqlparse.parse(query)[0]
                token = parsed.tokens
                _keyword = False
                _identifier = False
                size_flag=False
                choosecolumn = ''
                ref = ''
                tableflag = False
                tablename = ''
                validate=False
                where_clause=''
                groupby_flag=False
                out=''
                output=''
                invalid=''
                if str(token[0].ttype) == 'Token.Keyword.DML' and token[0].value.upper() == 'SELECT':
                    #print(token)
                    for i in token:
                        # print(str(i)+": "+str(i.ttype))
                        if str(i.ttype) == 'Token.Keyword' and i.value.upper() == 'GROUP BY':
                            groupby_flag=True
                        if groupby_flag and str(i.ttype) == 'None':
                            obj.get_groupbyclause(i)
                        if str(i.ttype) == 'Token.Literal.Number.Integer':
                            if size_flag:
                                obj.search_query['size']=str(i.value)
                        if str(i.ttype) == 'Token.Keyword' and i.value.upper() == 'LIMIT':
                            size_flag=True
                            for i in token:
                                if type(i) is sql.Where:
                                    where_clause=i
                                    break
                        if str(i.ttype) == 'Token.Wildcard':
                            choosecolumn = i.value
                        if str(i.ttype) == 'Token.Keyword' and i.value.upper() == 'FROM':
                            tableflag = True
                            if choosecolumn != '':
                                ref = choosecolumn
                            _keyword = True
                        if str(i.ttype) == 'None' and str(i) != '':
                            if tableflag:
                                tablename = i.value
                                tableflag = False
                            if _keyword:
                                _identifier = True
                            choosecolumn = i.value
                    if ref == '*' or ref == '':
                        pass
                    else:
                        innervalue = obj.getinnervalue(ref)
                        obj.search_query['_source']['includes'] = obj.search_query['_source']['includes']+innervalue
                        if groupby_flag:
                            for i in token:
                                if type(i) is sql.Where:
                                    where_clause=i
                                    break
                            obj.search_query['size']='0'
                            obj.aggregation_flag=True
                            tempflag=True
                            finaldict={}
                            for i in obj.grouplist:
                                tempdict={'aggregations':{i:{'terms':{}}}}
                                if tempflag:
                                    if 'aggregations' in obj.search_query.keys():
                                        tempdict['aggregations'][i]['aggregations']=obj.search_query['aggregations']
                                        tempdict['aggregations'][i]['terms']['field']=i+'.keyword'
                                        tempdict['aggregations'][i]['terms']['size']='5000'
                                        finaldict=tempdict
                                    else:
                                        tempdict['aggregations'][i]['terms']['field']=i+'.keyword'
                                        tempdict['aggregations'][i]['terms']['size']='5000'
                                        finaldict=tempdict
                                    tempflag=False    
                                else:
                                    tempdict['aggregations'][i]['aggregations']=finaldict['aggregations']
                                    tempdict['aggregations'][i]['terms']['field']=i+'.keyword'
                                    tempdict['aggregations'][i]['terms']['size']='5000'
                                    finaldict=tempdict
                                obj.search_query['aggregations']=finaldict['aggregations']
                        
                if _keyword and _identifier:
                    value=''
                    if size_flag or groupby_flag:
                        value=where_clause
                    else:
                        value=token[-1]
                    if str(value).upper().startswith('WHERE'):
                        whereclause = value
                        x = whereclause.tokens
                        if x[0].value.upper() == 'WHERE':
                            prevclause = ''
                            identifier = ''
                            for key in x:
                                if key.value.upper() == 'WHERE':
                                    continue
                                elif key.value == ' ':
                                    continue
                                elif type(key) is sql.Identifier:
                                    identifier = key.value
                                elif str(key.ttype) == 'Token.Keyword':
                                    prevclause = key.value.upper()
                                elif type(key) is sql.Parenthesis:
                                    innerdict = obj.getparenthesis(key, identifier, prevclause)
                                    if prevclause == 'IN':
                                        present = obj.getmustclause()
                                        if present:
                                            obj.search_query['query']['bool']['must'] = obj.search_query['query']['bool']['must']+[
                                                innerdict]
                                        else:
                                            obj.search_query['query']['bool']['must'] = [innerdict]
                                elif type(key) is sql.Comparison:
                                    innerdict = obj._comparison(key)
                                    if prevclause == 'AND' or prevclause == '':
                                        present = obj.getmustclause()
                                        if present:
                                            obj.search_query['query']['bool']['must'] = obj.search_query['query']['bool']['must']+[
                                                innerdict]
                                        else:
                                            obj.search_query['query']['bool']['must'] = [innerdict]

                                    elif prevclause == 'OR':
                                        present = obj.getshouldclause()
                                        if present:
                                            obj.search_query['query']['bool']['should'] = obj.search_query['query']['bool']['should']+[
                                                innerdict]
                                        else:
                                            obj.search_query['query']['bool']['should'] = [
                                                innerdict]
                        validate=True
                    else:
                        obj.search_query['query']['bool']['must'] = []
                        validate=True

                else:
                    invalid='Not a valid query'
                    output=''
                if 'compile' in request.POST:
                    if validate:
                        output=json.dumps(obj.search_query)
                        print(output)
                    else:
                        output=''
                        invalid='Not a valid query'
                    tcount=''
                    gtable=''
                    del obj
                if 'compileandrun' in request.POST:
                    gtable=''
                    if validate:
                        try:
                            url = "http://"+configs['IP']+"/"+str(tablename)+"/_search"
                            mainquery=(obj.search_query)
                            r = requests.post(url, data=json.dumps(mainquery))
                            tcount=''
                            out=''
                            output=''
                            res=''
                            gtable=''
                            if groupby_flag:
                                response = r.text
                                newdict=json.loads(response)
                                tcount=0
                                df=newdict['aggregations']
                                var=[item for item in obj.glist[::-1]]
                                print(var)
                                tlist=''
                                flist=''
                                x=''
                                if len(var)!=0:
                                    for i in range(0,len(var)):
                                        if i==0:
                                            tlist=[{"key":var[i],"variables":[{"elasticName":"doc_count","dfName":"count"}]}]
                                            flist=tlist
                                        else:
                                            tlist=[{"key":var[i],"aggs":flist}]
                                            flist=tlist
                                    r1list={}
                                    r2list=[]
                                    x=elasticToDataframe(df,flist,r1list,r2list)
                                    html = x.to_html(classes="table table-bordered table-striped mb-2")
                                    gtable=html
                                    out=''
                                else:
                                    out=''
                                    gtable=''
                            else:
                                response = r.text
                                newdict=json.loads(response)
                                tcount=0
                                tcount=newdict['hits']['total']
                                res = list(map(itemgetter('_source'),newdict['hits']['hits'] ))
                                out=res
                                gtable=''
                        except Exception as e:
                            print(e)
                            out=''
                            tcount=''
                        output=''
                    else:
                        output=''
                        tcount=''
                        invalid='Not a valid query!'
                    del obj
                context={
                    'input':str(query),
                    'output':output,
                    'invalid':invalid,
                    'out':out,
                    'gtable':gtable,
                    'count':tcount
                }
                return render(request,'pages/index.html',context)
            else:
                return render(request,'pages/index.html')
        except Exception as e:
            print(e)
            return render(request,'pages/error.html')
    else:
        context={
                    'input':str(query),
                    'output':output,
                    'invalid':'Not a valid submission',
                    'out':out,
                    'gtable':gtable
                }
        return render(request,'pages/error.html')
 
