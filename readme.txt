# install dependencies on Ubuntu
sudo apt-get install python-virtualenv libcurl4-openssl-dev python-dev 

# install dependencies on Mac
brew install curl
ARCHFLAGS="-arch x86_64" LDFLAGS=-L$HOMEBREW/opt/curl/lib CPPFLAGS=-I$HOMEBREW/opt/curl/include pip install pycurl

git clone https://github.com/xiaoruoruo/zhishi.me

cd zhishi.me

# setup virtualenv, only need this for the first time
virtualenv .

# enable virtualenv
. bin/activate

# install python dependencies
pip install -r requirement.txt

cd src

# recompile the template into python code
cheetah-compile base.tmpl

export AG_PASSWORD=allegro_graph_password

# for local development, run
python index.py

# for production, run
gunicorn -c gunicorn_conf.py index

