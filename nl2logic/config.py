import yaml
import json
import os
from types import SimpleNamespace
import logging
import logging.handlers

nl2logic_config = None
_raw_nl2logic_config = None

_logging_level = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
}

def load_config(path=None):
    global nl2logic_config, _raw_nl2logic_config

    if path is None:
        path = os.environ.get("NL2LOGIC_CONFIG", "./nl2logic_config.yaml")
    with open(path, "r", encoding="UTF-8") as config_file:
        _raw_nl2logic_config = yaml.safe_load(config_file.read())

    # Convert to SimpleNamespace to access with a.b.c style notations instead of dict
    def load_object(_raw_nl2logic_config):
        return SimpleNamespace(**_raw_nl2logic_config)
    nl2logic_config = json.loads(json.dumps(_raw_nl2logic_config), object_hook=load_object)
load_config()

def set_logger(task: str):
    log_config = getattr(nl2logic_config.log, task)
    try:
        # Set global logger
        logging.basicConfig(level=_logging_level[log_config.level])
    except KeyError:
        logging.error(f"Cannot find config level `{log_config.level}`: try in {_logging_level.keys()}")
    
    f = logging.Formatter(fmt='%(levelname)s:%(name)s: %(message)s '
    '(%(asctime)s; %(filename)s:%(lineno)d)',
    datefmt="%Y-%m-%d %H:%M:%S")
    handlers = [
        logging.handlers.TimedRotatingFileHandler(
            os.path.join(log_config.directory, log_config.filename),
            when='midnight',
            encoding='utf8',
            backupCount=1
        ),
        logging.StreamHandler()
    ]
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers.clear()
    for h in handlers:
        h.setFormatter(f)
        h.setLevel(logging.INFO)
        root_logger.addHandler(h)

    logging.info("Load config / set logger complete")
    logging.info("\n" + yaml.dump(_raw_nl2logic_config) + "\n")