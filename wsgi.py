import os
from api import init

if __name__ == "__main__":
    auth_key = os.environ.get("BRAVIA_API_KEY")
    tv_host = os.environ.get("BRAVIA_DEVICE_HOST")
    tv_psk = os.environ.get("BRAVIA_DEVICE_PASSCODE")

    init(auth_key, tv_host, tv_psk)
