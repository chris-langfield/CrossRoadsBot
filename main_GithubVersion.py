import tweepy as tw
from PIL import Image
import requests
from io import BytesIO
import random 
import json
import csv
import time
#### KEYS
GoogleMapsStaticAPIKey = ''
# twitter keys
CustomerApiKey = ""
CustomerApiKeySecret = ""
AccessToken = ""
AccessTokenSecret = ""


# Authenticate to Twitter
auth = tw.OAuthHandler(CustomerApiKey, CustomerApiKeySecret)
auth.set_access_token(AccessToken, AccessTokenSecret)

# Create API object
api = tw.API(auth,wait_on_rate_limit=True,
    wait_on_rate_limit_notify=True)

bboxLatHalfWidth = 0.002
bboxLonHalfWidth = 0.005

overpass_url = "http://overpass-api.de/api/interpreter"

count = 0
while count < 100:
    # current timestamp
    imageFileName = str(int(time.time()))
    # get a random pair of coordinates
    rLat = 0
    rLon = 0
    CityName = ''
    Country = ''
    with open('worldcities.csv',encoding="utf-8") as CitiesDB:
        Cities = csv.reader(CitiesDB)
        randRow = []
        
        notUSA = random.choice([True,False])
        listCities = list(Cities)
        if notUSA:
            while True:
                randRow = random.choice(listCities)
                if not randRow[6] == 'USA':
                    break
        else:
            randRow = random.choice(listCities)
        rLat = float(randRow[2])
        rLon = float(randRow[3])
        CityName = randRow[1]
        Country = randRow[4]
    print(rLat)
    print(rLon)
    print(CityName)
    print(Country)

    # offset center point randomly
    rLat += random.uniform(-0.05,0.05)
    rLon += random.uniform(-0.05,0.05)
    bbox1 = str(round(rLat-bboxLatHalfWidth,5))
    bbox2 = str(round(rLon-bboxLonHalfWidth,5))
    bbox3 = str(round(rLat+bboxLatHalfWidth,5))
    bbox4 = str(round(rLon+bboxLonHalfWidth,5))
    bbox = '{0},{1},{2},{3}'.format(bbox1,bbox2,bbox3,bbox4)
    print(bbox)    

    # setup query       
    overpass_query = """
    [out:json]
    [timeout:300]
    [bbox:""" + bbox + """];
    way[highway]->.major;
    way[highway]->.minor;
    foreach.major->.a(
        foreach.minor->.b(
            node(w.a)(w.b)->.coords;
            .a out tags;
            .b out tags;
            .coords out body;       
        );
    );
    """

    # send query 
    response = requests.get(overpass_url, 
                            params={'data': overpass_query})
    # print HTTP response
    print(str(response))
    if '200' not in str(response):
        continue
    
    data = response.json()

    scrapedData = []
    with open('response.txt','w') as f:
        json.dump(data, f, indent=4)
    with open('response.txt','r') as f:
        flines = f.readlines()
        for i in range(len(flines)):
            if 'type": "way' in flines[i]:
                wayId = 'w' + flines[i+1].split(':')[1][1:-2]
                scrapedData.append(wayId)
            if 'type": "node' in flines[i]:
                nodeId = 'n' + flines[i+1].split(':')[1][1:-2]
                scrapedData.append(nodeId)
    for x in range(min(len(scrapedData),20)):
        print (scrapedData[x])

    potentialIntersections = []
    for x in range(len(scrapedData)-2):
        # if this is a way, and the following element is a way,
        # and they aren't the same way
        # and the one after those two is a node
        if scrapedData[x][0] == 'w' and scrapedData[x+1][0] == 'w' and not scrapedData[x][1:] == scrapedData[x+1][1:] and scrapedData[x+2][0] == 'n':
            potentialIntersections.append([scrapedData[x],scrapedData[x+1],scrapedData[x+2]])
    for x in range(min(len(potentialIntersections),20)):
        print (potentialIntersections[x])
    ### now open file as json, find the relevant ids. Make sure the streets have names.
    ### then find the node, get the lat and long, and plug into Google Maps url
    #data = []
    #with open('response.txt','r') as f:
        #data = json.load(f)
    elements = data["elements"]
    potentialIntersectionsNamesCoords = []
    
    for x in potentialIntersections:
        tempWay0 = ''
        tempWay1 = ''
        lat = ''
        lon = ''
        for elem in elements:
            if elem["type"]=="way" and str(elem["id"])==x[0][1:]:
                if "tags" in elem and "name" in elem["tags"]: 
                    tempWay0 = elem["tags"]["name"]
        for elem in elements:
            if elem["type"]=="way" and str(elem["id"])==x[1][1:]:
                if "tags" in elem and "name" in elem["tags"]:
                    tempWay1 = elem["tags"]["name"]
        
        if tempWay0 not in [''] and tempWay1 not in ['']:
            for elem in elements:
                if elem["type"]=="node" and str(elem["id"])==x[2][1:]:
                    lat = elem["lat"]
                    lon = elem["lon"]
                    if [tempWay0,tempWay1,lat,lon] not in potentialIntersectionsNamesCoords:
                        potentialIntersectionsNamesCoords.append([tempWay0,tempWay1,lat,lon])
    
    copy = potentialIntersectionsNamesCoords.copy()
    for x in copy:
        if x[0] in x[1] or x[1] in x[0]:
            potentialIntersectionsNamesCoords.remove(x)
    for x in potentialIntersectionsNamesCoords:
        print( x)

    if not potentialIntersectionsNamesCoords:
        print("no intersections found")
        count += 1
        continue
            
    randomIntersection = random.choice(potentialIntersectionsNamesCoords)

    StatusText = randomIntersection[0] + ' and ' + randomIntersection[1] + '. Near ' + CityName + ', ' + Country + '.'
    print(StatusText)
    ## get image from google maps api
    googleUrl = "https://maps.googleapis.com/maps/api/staticmap?center="+str(randomIntersection[2])+","+str(randomIntersection[3])+"&zoom=18&size=800x800&format=png&maptype=satellite&key=" + GoogleMapsStaticAPIKey
    response = requests.get(googleUrl)
    img = Image.open(BytesIO(response.content))
    img.save('images/{}.png'.format(imageFileName))
    
    api.update_with_media('images/{}.png'.format(imageFileName),status=StatusText)
    api.update_profile(description = 'We all face crossroads in life.\n\nI most recently visited ' + CityName + ', ' + Country + '.')                                                                                                           

    timeLast = time.time()
    while time.time() - timeLast < 3600.0:
        pass
    print('tweeting again')
    
    count += 1
        
    
    
    

