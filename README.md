# mastodon-crawler
Crawler to find the followings of the following list of an account

***
## Prerequisites
To run the crawler docker must be installed on the machine.

## Installation
First the container must be built via the terminal inside the projects folder via the command:

```
docker compose build
```

To start the program you can use the command:

```
docker compose up
```

## Usage
Using the endpoint https://localhost:8080/get_followings with the parameter of the account to search.
Format of the parameter: 
```
@username@instance_name
``` 
Example request running on a local machine: 

```
https://localhost:8080/get_followings?parameter=@Gargron@mastodon.social
```
