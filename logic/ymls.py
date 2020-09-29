import yaml, os, csv

INFO = {}
INFO_FILE_NAME = 'info.yml'
CONFIG = {}
CONFIG_FILE_NAME = 'config.yml'
SECRET = {}
SECRET_FILE_NAME = 'secret.yml'

try:
    with open(INFO_FILE_NAME) as f:
        INFO = dict(yaml.load(f, Loader = yaml.FullLoader))
except:
    with open(INFO_FILE_NAME, 'w') as f:
        yaml.dump(INFO, f)
try:
    with open(CONFIG_FILE_NAME) as f:
        CONFIG = dict(yaml.load(f, Loader = yaml.FullLoader))
except:
    with open(CONFIG_FILE_NAME, 'w') as f:
        yaml.dump(CONFIG, f)
try:
    with open(SECRET_FILE_NAME) as f:
        SECRET = dict(yaml.load(f, Loader = yaml.FullLoader))
except:
    with open(SECRET_FILE_NAME, 'w') as f:
        yaml.dump(SECRET, f)

def save_info():
    with open(INFO_FILE_NAME, 'w') as f:
        yaml.dump(INFO, f)

def save_config():
    with open(CONFIG_FILE_NAME, 'w') as f:
        yaml.dump(CONFIG, f)