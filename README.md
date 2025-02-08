# yt-download

⚠️⚠️
This project is a test project **to play and learn docker** 
objective is to have a node server listening to post with a url and with that url use the yt-dlp util to actually download the video and save it

**NOTE**: there is little to no check in place this is a purely test and learn project

## Download the video

Post a json to  `http://localhost:3000/download` formated as follow

```json
 {
     "url": "URL_OF_THE_VIDEO"
 }
```

## Check status
call get to  `http://localhost:3000/status` will return the list of downloads with their statuses

## Dependencies
Node, UUID, express and yt-dlp

