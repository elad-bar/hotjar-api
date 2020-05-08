# Hotjar API

## Description
Provides an easy way to integrate as data source Hotjar to analytics tools,
On the first run, the container will try to get all data since the funnel creation date until now,
from that point, it will do an incremental update,
the last day will get updates along the day according to the chosen update interval.

[Changelog](https://github.com/elad-bar/hotjar-api/blob/master/CHANGELOG.md)

## Environment Variables
```
HOTJAR_USERNAME	    Username of Hotjar account
HOTJAR_PASSWORD	    Password of Hotjar account
HOTJAR_FUNNELS		Optional, CSV formated funnel Ids of funnels to work with, an empty value will work with all funnels
HOTJAR_INTERVAL		Interval in minutes between fetching data from Hotjar
API_KEY             Optional, protected the API with secret API key
```

## How to run

#### Data persistence
By default the container is being created with volume /data,
To allow faster load (with less API calls), define local (host) path as volume.

Data will be fully reloaded when there is a major version change

#### Docker Run
```
docker run -p 5000:5000 --restart always -v /data_host:/data -e HOTJAR_USERNAME=Username -e HOTJAR_PASSWORD=Password -e HOTJAR_FUNNELS= -e HOTJAR_INTERVAL=30 -e API_KEY=APIKEY --name "hotjar-api" eladbar/hotjar-api:latest
```

#### Docker Compose
```
version: '2'
services:
    hotjar-api:
        ports:
            - '5000:5000'
        restart: always
        volumes:
            - '/data_host:/data'
        environment:
            - HOTJAR_USERNAME=Username
            - HOTJAR_PASSWORD=Password
            - HOTJAR_FUNNELS=
            - HOTJAR_INTERVAL=30
            - API_KEY=APIKey
        container_name: hotjar-api
        image: 'eladbar/hotjar-api:latest'
```

## API Endpoints
#### With API_KEY
Request should be with query string parameter APIKEY (Case Sensitive): <br/>
http://IP/json?APIKEY=APIKey

#### /
```json
{
  "records": 1, 
  "sites": 1, 
  "version": "1.0"
}
```

Description:
```
Root object
    records             Number of records reterived from Hotjar
    sites               Number of sites
    version             Version of Hotjar-API
```

#### /json
```json
{
  "{SITE_ID}": {
    "funnels": {
      "{FUNNEL_ID}": {
        "created": 1578997746,            
        "created_iso": "2020-01-14",      
        "id": 1,                          
        "last_update": 1585958400,        
        "last_update_iso": "2020-04-04",  
        "name": "{FUNNEL_NAME}",          
        "steps": {
          "{FUNNEL_STEP_ID}": {
            "counters": {                 
              "2020-01-14": {              
                "count": 283,             
                "epoch": 1578952800       
              }
            },
            "id": 1,                      
            "name": "",                   
            "url": ""                     
          }
        }
      }
    },
    "id": 1,                              
    "name": "{SITE_NAME}"                 
  }
}
```

Description:
```
Root object - Dictionary of Site Id and Site Object

Site Object
    id                  Site Id
    name                Site name
    funnels             Dictionary of Funnel Id and Funnel Object

Funnel Object
    created             Created date (Epoch format)
    created_iso         Created date (ISO format)
    id                  Funnel id
    last_update         Last update (Epoch format) - Counters updated to
    last_update_iso     Last update (ISO format) - Counters updated to
    name                Funnel name
    steps               Dictionary of Funnel Step Id and Funnel Step Object

Funnel Step Object
    id                  Funnel step id
    name                Funnel step name
    url                 Funnel step URL
    counters            Dictionary of date (ISO format) and Funnel Step Counter Object

Funnel Step Counter Object
    count               Count
    epoch               Date (Epoch format)
```


#### /flat
```json
[
  {
    "count": 1, 
    "date": "Sat, 04 Apr 2020 00:00:00 GMT", 
    "date_epoch": 1585958400, 
    "date_iso": "2020-04-04", 
    "funnel_created": 1585985207, 
    "funnel_id": "", 
    "funnel_name": "", 
    "funnel_step_id": "", 
    "funnel_step_name": "", 
    "funnel_step_url": "", 
    "site_id": "", 
    "site_name": ""
  }
]
```

Description
```
Root object - Array of Measurment Object

Measurment Object
    site_id             Site Id
    site_name           Site name
    funnel_id           Funnel id
    funnel_name         Funnel name
    funnel_step_id      Funnel step id
    funnel_step_name    Funnel step name
    funnel_step_url     Funnel step URL
    count               Count
    date_epoch          Date (Epoch format)
    date_iso            Date (ISO format)
```
