#!/bin/bash

sudo certbot renew --manual --preferred-challenges=dns

sudo cp /etc/letsencrypt/live/chamyeongdo.iptime.org/fullchain.pem ssl/
sudo cp /etc/letsencrypt/live/chamyeongdo.iptime.org/privkey.pem ssl/
sudo chown $USER:$USER ssl/*

docker-compose restart nginx
