from ruamel.yaml import YAML

FILENAME = 'exv2/config.yaml'

def load_config():
    raw_yaml = open(FILENAME).read()
    cfg = YAML().load(raw_yaml)
    return cfg
