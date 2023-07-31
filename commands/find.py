from telegram import Update
from telegram.ext import ContextTypes
import services.rightmove_service as rms
import services.json_service as json_service
import services.driver_service as driver_service
import random
import time


async def find_properties_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # get environment variables
    debug_config = json_service.get_application_config()["debug_config"]

    # get our search criteria
    search_criteria = json_service.get_search_criteria()

    # generate urls from criteria
    urls = rms.generate_rightmove_urls(search_criteria)

    # let user know search is beginning
    await update.message.reply_text("Checking for new properties")

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

    propertiesToShow = []
    for property in properties:
        exists = json_service.check_duplicate_property_exists(property)
        if exists == 0:
            propertiesToShow.append(property)
            json_service.add_property_to_json(property)
            stringLimit = "\n"
            text = f"Price: {property[0].split(stringLimit)[0]}{stringLimit}Location: {property[1]}{stringLimit}View More: {property[4]}"

            await update.message.reply_text(text)

    if len(propertiesToShow) == 0:
        await update.message.reply_text(
            "Aw, no new properties have been found for your criteria :("
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
