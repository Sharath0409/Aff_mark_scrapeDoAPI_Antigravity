import logging
import sys

def get_logger(name):
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # Stream handler
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(formatter)
        logger.addHandler(sh)
        
        # File handler (optional)
        # fh = logging.FileHandler('app.log')
        # fh.setFormatter(formatter)
        # logger.addHandler(fh)
    return logger
