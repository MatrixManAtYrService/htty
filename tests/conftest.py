import logging

# Configure logging for htty tests
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# Enable debug logging for htty
logging.getLogger("htty.core").setLevel(logging.DEBUG)
