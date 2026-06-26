import sys
from keep_alive import keep_alive
from . import bot
import logging
from . import config

if __name__ == "__main__":
    formatter = logging.Formatter(
        fmt="[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s"
    )

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    file_handler = logging.FileHandler("bot.log", encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Create a StreamHandler for stdout
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    keep_alive()
    bot.run()