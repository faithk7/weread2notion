import logging
from datetime import datetime

# Create a formatter
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# Create and configure the logger
logger = logging.getLogger("weread2notion")
logger.setLevel(logging.INFO)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# File handler
current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
file_handler = logging.FileHandler(f"weread2notion_{current_time}.log")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
