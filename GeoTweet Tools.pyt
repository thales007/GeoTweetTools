#######################################
# Title: GeoTweets Toolbox
# Description: Python toolbox for ArcGIS 10.1
# Author: Timothy Hales
# Date: 1/16/2013
# Version: 1.0
# Python Version: 2.7
# Twitter API 1.0
#######################################

#import modules for GeoTweets tool
import arcpy, pythonaddins, os, sys, urllib2, webbrowser

try:
    import simplejson as json
except ImportError:
    import json

#import modules for Keyword Parser tool
import string, re
import decimal
from decimal import *

class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "GeoTweets"
        self.alias = "GeoTweets"

        # List of tool classes associated with this toolbox
        self.tools = [GeoTweetsXY, GeoTweetsFC, KeywordParser]

class GeoTweetsXY(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "GeoTweets by XY"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        radius = arcpy.Parameter(
            displayName="Search Radius",
            name="radius",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")
        units = arcpy.Parameter(
            displayName="Search Units",
            name="units",
            datatype="gpString",
            parameterType="Required",
            direction="Input")
        units.filter.type = "ValueList"
        units.filter.list = ["mi", "km"]
        units.value = "mi"
        outputPath = arcpy.Parameter(
            displayName="Output Tweet Table",
            name="outputPath",
            datatype="DETable",
            parameterType="Required",
            direction="Output")
        searchX = arcpy.Parameter(
            displayName="Search X Coordinate",
            name="Xcoordinate",
            datatype="GPDouble",
            parameterType="Required",
            direction="input")
        searchY = arcpy.Parameter(
            displayName="Search Y Coordinate",
            name="Ycoordinate",
            datatype="GPDouble",
            parameterType="Required",
            direction="input")

        #load the parameters        
        parameters = [searchX, searchY, radius, units, outputPath]
        return parameters
    
    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        #define variables for input parameters
        pointX = parameters[0].valueAsText
        pointY = parameters[1].valueAsText
        radius = parameters[2].valueAsText + parameters[3].valueAsText
        geo = str(pointX) + "," + str(pointY) + "," + str(radius)
        tweetTable = parameters[4].valueAsText
        arcpy.env.overwriteOutput = 1

        #Create Tweet Table
        dir2 = os.path.dirname(tweetTable)
        file2 = os.path.basename(tweetTable)
        twiTable = arcpy.CreateTable_management(dir2, file2)

        #Add Fields
        arcpy.AddField_management(twiTable, "UserName", "TEXT")
        arcpy.AddField_management(twiTable, "Tweet", "TEXT")
        arcpy.AddField_management(twiTable, "TweetTime", "TEXT")
        arcpy.AddField_management(twiTable, "TweetID", "TEXT")
        arcpy.DeleteField_management(twiTable, "ID")

        #Retrieve Tweets
        def searchAll(page='',geo=''): 
            """ use search api to find tweets matching a query string and/or 
                location as string of "lat,lon,radius", see api documentation"""
            query = 'http://search.twitter.com/search?&format=json&rpp=100&page=%s&result_type=recent&geocode=%s' % (page,geo)
            f = urllib2.urlopen(query)
            r = json.loads(f.read())
            return r["results"]

        def search(q='',page='',geo=''): 
            """ use search api to find tweets matching a query string and/or 
                location as string of "lat,lon,radius", see api documentation"""
            query = 'http://search.twitter.com/search?q=%s&format=json&rpp=100&page=%s&result_type=recent&geocode=%s' % (q,page,geo)
            f = urllib2.urlopen(query)
            r = json.loads(f.read())
            return r["results"]           
            
        def parse(res):
            """ take the relevant parts of the result"""
            #list of tuples (user,time,text,geo, id)
            return [(r['from_user'],r['text'],r['created_at'],r['id'],r['geo']) 
                    for r in res if r['geo'] != None]

        geo = str(pointY) + "," + str(pointX) + "," + str(radius)
        pagelist = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15]
        twiList = []

        #Search each resutls page
        for pg in pagelist:
            #query Search API
            output = parse(searchAll(page=pg,geo=geo))
               
            for twi in output:
                twiName = str(twi[0])
                twiText = str(twi[1].encode('ascii', 'ignore'))
                twiTime = str(twi[2])
                twiID = twi[3]
                #OverflowError: Python int too large to convert to C long
                twiX = twi[4]['coordinates'][1]
                twiY = twi[4]['coordinates'][0]

                if twiX != 0 and twiY != 0:
                    twiData = twiName, twiText.replace("&lt;", "<").replace("&amp;","&"), twiTime, str(twiID)
                    twiList.append(twiData)
                
        insCur = arcpy.da.InsertCursor(twiTable, ("UserName","Tweet","TweetTime","TweetID"))
        #print len(twiList)
        for twi2 in twiList:
            insCur.insertRow(twi2)

        del insCur
        tag = None
        geo = None

class GeoTweetsFC(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "GeoTweets by Feature Class"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        inputFC = arcpy.Parameter(
            displayName="Input Point Feature Class",
            name="inputFC",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input")
        locationID = arcpy.Parameter(
            displayName="Location ID",
            name="locationID",
            datatype="gpString",
            parameterType="Required",
            direction="Input")
        locationID.filter.type = "ValueList"
        locationID.filter.list = [" "]
        inputFC.filter.list = ["Point"]
        radius = arcpy.Parameter(
            displayName="Search Radius",
            name="radius",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")
        units = arcpy.Parameter(
            displayName="Search Units",
            name="units",
            datatype="gpString",
            parameterType="Required",
            direction="Input")
        units.filter.type = "ValueList"
        units.filter.list = ["mi", "km"]
        units.value = "mi"
        outputPath = arcpy.Parameter(
            displayName="Output Tweet Table",
            name="outputPath",
            datatype="DETable",
            parameterType="Required",
            direction="Output")

        #load the parameters        
        parameters = [inputFC, locationID, radius, units, outputPath]
        return parameters
    
    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        if parameters[0].value:
            fields = arcpy.ListFields(parameters[0].ValueAsText)
            fieldNames = [f.name for f in fields]
            parameters[1].filter.list = fieldNames

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        if parameters[0].value:
            descFC = arcpy.Describe(parameters[0].value).spatialReference  
            if descFC.GCSCode == 0:
                parameters[0].setErrorMessage("You point feature class is set to a projected coordinate system.  This tool requires the point feature class to have a geographic coordinate system")

    def execute(self, parameters, messages):
        """The source code of the tool."""
        #define variables for input parameters
        tweetTable = parameters[4].valueAsText
        arcpy.env.overwriteOutput = 1

        #Create Tweet Table        
        dir2 = os.path.dirname(tweetTable)
        file2 = os.path.basename(tweetTable)
        twiTable = arcpy.CreateTable_management(dir2, file2)

        #Add Fields
        arcpy.AddField_management(twiTable, "UserName", "TEXT")
        arcpy.AddField_management(twiTable, "Tweet", "TEXT")
        arcpy.AddField_management(twiTable, "TweetTime", "TEXT")
        arcpy.AddField_management(twiTable, "TweetID", "TEXT")
        arcpy.AddField_management(twiTable, "Location", "TEXT")
        arcpy.DeleteField_management(twiTable, "Feild1")

        #define variable for input point feature class        
        pointFC = parameters[0].ValueAsText
        ptCur = arcpy.da.SearchCursor(pointFC, ("Name", "SHAPE@X" , "SHAPE@Y"))
        
        #Search Tweets for each point in Feature Class
        for pt in ptCur:    
            pointX = pt[1]
            pointY = pt[2]
            radius = parameters[2].valueAsText + parameters[3].valueAsText
            geo = str(pointX) + "," + str(pointY) + "," + str(radius)
            arcpy.AddMessage("Searching: " + pt[0])

            #Retrieve Tweets
            def searchAll(page='',geo=''): 
                """ use search api to find tweets matching a query string and/or 
                    location as string of "lat,lon,radius", see api documentation"""
                query = 'http://search.twitter.com/search?&format=json&rpp=100&page=%s&result_type=recent&geocode=%s' % (page,geo)
                f = urllib2.urlopen(query)
                r = json.loads(f.read())
                return r["results"]

            def search(q='',page='',geo=''): 
                """ use search api to find tweets matching a query string and/or 
                    location as string of "lat,lon,radius", see api documentation"""
                query = 'http://search.twitter.com/search?q=%s&format=json&rpp=100&page=%s&result_type=recent&geocode=%s' % (q,page,geo)
                f = urllib2.urlopen(query)
                r = json.loads(f.read())
                return r["results"]           
                
            def parse(res):
                """ take the relevant parts of the result"""
                #list of tuples (user,time,text,geo, id)
                return [(r['from_user'],r['text'],r['created_at'],r['id'],r['geo']) 
                        for r in res if r['geo'] != None]

            geo = str(pointY) + "," + str(pointX) + "," + str(radius)
            pagelist = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15]
            twiList = []
            
            #Search each resutls page
            for pg in pagelist:
                #query Search API
                output = parse(searchAll(page=pg,geo=geo))
                   
                for twi in output:
                    twiName = str(twi[0])
                    twiText = str(twi[1].encode('ascii', 'ignore'))
                    twiTime = str(twi[2])
                    twiID = twi[3]
                    #OverflowError: Python int too large to convert to C long
                    twiX = twi[4]['coordinates'][1]
                    twiY = twi[4]['coordinates'][0]

                    if twiX != 0 and twiY != 0:
                        twiData = twiName, twiText.replace("&lt;", "<").replace("&amp;","&"), twiTime, str(twiID), pt[0]
                        twiList.append(twiData)
                    
            insCur = arcpy.da.InsertCursor(twiTable, ("UserName","Tweet","TweetTime","TweetID", "Location"))
            arcpy.AddMessage(str(len(twiList)) + " Tweets found for " + pt[0])
            for twi2 in twiList:
                insCur.insertRow(twi2)

            del insCur
            tag = None
            geo = None
            
#Keyword tool
class KeywordParser(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Keyword Parser"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        inputTable = arcpy.Parameter(
            displayName="Input Table",
            name="inputTable",
            datatype="DETable",
            parameterType="Required",
            direction="Input")
        searchField = arcpy.Parameter(
            displayName="Field",
            name="searchField",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        searchField.filter.type = "ValueList"
        outputTable = arcpy.Parameter(
            displayName="Output Table",
            name="outputTable",
            datatype="DETable",
            parameterType="Required",
            direction="Output")
        numKeywords = arcpy.Parameter(
            displayName="Top Keywords",
            name="numKeywords",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")
        exWords = arcpy.Parameter(
            displayName="Exclude Words",
            name="exWords",
            datatype="gpString",
            parameterType="optional",
            direction="Input")       

        #load the parameters        
        parameters = [inputTable, searchField, outputTable, numKeywords, exWords]
        return parameters
    
    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        if parameters[0].value:
            fields = arcpy.ListFields(parameters[0].ValueAsText)
            fieldNames = [f.name for f in fields]
            parameters[1].filter.list = fieldNames

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        #Create output table
        tablePath = parameters[2].ValueAsText        
        outputTablePath = os.path.dirname(tablePath)
        outputTableName = os.path.basename(tablePath)
        outputTable = arcpy.CreateTable_management(outputTablePath, outputTableName)
        
        arcpy.AddField_management(outputTable, "Keyword", "TEXT")
        arcpy.AddField_management(outputTable, "Count", "Integer")
        arcpy.AddField_management(outputTable, "Total", "Integer")
        arcpy.AddField_management(outputTable, "Percent", "Double")
        arcpy.DeleteField_management(outputTable, "Field1")
   
        table = parameters[0].ValueAsText
        tList = []
        cur = arcpy.SearchCursor(table)

        field = parameters[1].ValueAsText        

        for row in cur:
            tList.append(row.getValue(field))

        text = ' '.join(tList)

        def sort_by_value(d): 
            u""" Returns the keys of dictionary d sorted by their values """ 
            items=d.items()
            backitems=[ [v[1],v[0]] for v in items] 
            backitems.sort() 
            return [ backitems[i][1] for i in range(0,len(backitems))] 

        def get_most_used_words(text, n):
            #Returns the top used words in a text field
            
            #Convert text to lowercase
            text =  text.lower()  

            #Replace seperators with spaces
            seperators = "\n\r\f\t\v.,/\\""''"
            for seperator in seperators:
                text = text.replace(seperator, " ")
            
            #Remove non-alpha characters 
            validchars = "abcdefghijklmnopqrstuvwxyz "
            
            charlist = list(text.lower())
            charlist = [char for char in charlist if char in validchars]
            text = "".join(charlist)
            
            #Split up the words
            words  = text.split(" ")
            
            #Remove the spaces
            words = [word for word in words if word != " "]
            
            #Sort the words
            words.sort()
            
            #Define common words to filter
            
            commonList = "about, and, are, but, for, from, have, http, just, like, some, still, the, that, then, they, this, was, what, when, will, with, would, you, your, " + str(parameters[4].ValueAsText).lower()
            arcpy.AddMessage("Excluded words: " + str(commonList))

            #define the word dictionary
            global wordDictionary
            wordDictionary = {}
            for word in words:
                #allow 3 letter words and larger
                if len(word) > 3:
                    #check to make sure word is not on common list
                        if word not in commonList:
                            wordDictionary[word] = wordDictionary.get(word,0) + 1
           
            #use only the top words
            top =  sort_by_value(wordDictionary)[-n:]
            
            #remove sort
            #top.sort()
            #reverse sort to be largest to smallest
            top.reverse()
            
            return " ".join(top)

        topNumber = int(parameters[3].ValueAsText)
        topList = get_most_used_words(text,topNumber)
        topSplit = topList.split(" ")

        wordTotal = len(re.findall(r'\w+', text))

        rows = arcpy.da.InsertCursor(outputTable, ("Keyword", "Count","Total", "Percent"))

        for tL in topSplit:
            wordCount = wordDictionary.get(tL)
            getcontext().prec = 4
            percent = Decimal(wordCount)/Decimal(wordTotal)
            
            values = tL, wordCount, wordTotal, percent

            rows.insertRow(values)
