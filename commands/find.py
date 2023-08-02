import services.rightmove_service as rms
import services.json_service as json_service
import services.driver_service as driver_service
import random
import time

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from services.telegram_message_service import search_message, property_message
from logger.logger import getMyLogger
from html import escape
from objects.property import property as p

logger = getMyLogger(__name__)


async def find_properties_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # let user know search is beginning
    await update.message.reply_text(
        search_message(0, "", ""), parse_mode=ParseMode.HTML
    )

    logger.info(
        "%s asked to find %d (%s)"
        % (
            escape(update.message.from_user.first_name),
            update.message.chat_id,
            escape(update.message.text),
        )
    )

    # get environment variables
    debug_config = json_service.get_application_config()["debug_config"]

    # get our search criteria
    search_criteria = json_service.get_search_criteria()

    # generate url objects from criteria {location, url}
    urlInfo = rms.generate_rightmove_urls(search_criteria)

    # let user know search is beginning
    await update.message.reply_text(
        search_message(1, "", ""), parse_mode=ParseMode.HTML
    )

    properties = []

    # create our webdriver for this scrape
    driver = driver_service.Create()

    # do scrape only if config says so - to speed up testing.
    if debug_config["run_scrape"] == 1:
        for info in urlInfo:
            # simulate real use of site by waiting 5-15 seconds
            rnd = random.randint(5, 15)
            time.sleep(rnd)

            # begin scrape for location
            result = rms.scrape_rightmove_properties(driver, info["url"])

            # let user know how many properties we've scraped and were the location is in a fun way
            await update.message.reply_text(
                search_message(2, str(len(result)), info["name"]),
                parse_mode=ParseMode.HTML,
            )
            properties.extend(result)
    else:
        properties.extend(
            [
                p(
                    price="£150000\n",
                    address="Formby",
                    bathrooms=1,
                    beds=1,
                    pictures="",
                    description="",
                    url="https://hello-world-test.com",
                )
            ]
        )

    propertiesToShow = []
    for property in properties:
        # have we shown this property before?
        exists = json_service.check_duplicate_property_exists(property)

        # if not
        if exists == 0:
            # show user property
            print(property, search_criteria)
            await update.message.reply_text(
                property_message(property, search_criteria), parse_mode=ParseMode.HTML
            )

            # add property to json temp db
            propertiesToShow.append(property)
            json_service.add_property_to_json(property)

    # let user know if no properties
    if len(propertiesToShow) == 0:
        await update.message.reply_text(
            search_message(3, "", ""), parse_mode=ParseMode.HTML
        )


async def find_callback(context):
    chat_id = context.job.chat_id

    # get environment variables
    debug_config = json_service.get_application_config()["debug_config"]

    # get our search criteria
    search_criteria = json_service.get_search_criteria()

    # generate urls from criteria
    urls = rms.generate_rightmove_urls(search_criteria)

    properties = []

    # create our driver for this scrape
    driver = driver_service.Create()

    # iterate over urls if we have a value run_scrape
    if debug_config["run_scrape"] == 1:
        for url in urls:
            rnd = random.randint(5, 15)
            time.sleep(rnd)
            properties.extend(rms.scrape_rightmove_properties(driver, url))
    else:
        properties.extend(
            [
                {
                    "price": "£150000\n",
                    "address": "Formby",
                    "propertyType": "New Build",
                    "bathroom": 1,
                    "propertyLink": "https://hello-world-test.com",
                }
            ]
        )

    new_properties = []
    for property in properties:
        exists = json_service.check_duplicate_property_exists(property)
        if exists == 0:
            new_properties.append(property)
            json_service.add_property_to_json(property)
            stringLimit = "\n"
            text = f"Price: {property[0].split(stringLimit)[0]}{stringLimit}Location: {property[1]}{stringLimit}View More: {property[4]}"
            await context.bot.send_message(chat_id=chat_id, text=text)
