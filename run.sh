#!/bin/bash
cd /home/apex/zhishi.me
. bin/activate
cd src
gunicorn -c gunicorn_conf.py index

