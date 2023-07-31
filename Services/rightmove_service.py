from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from objects.criteria import criteria
from services.driver_service import *
from objects.property import property


# scraping method
def scrape_rightmove_properties(drive: webdriver, url: str):
    rows = []
    try:
        driver = goto(drive, url)
        waitForPageLoad(driver)
        pagination = CreateSelect(
            driver, By.CLASS_NAME, "pagination-dropdown", "Could not find pagination"
        )
        for index in range(len(pagination.options)):
            propertyCards = getHTMLGroups(
                driver, By.CLASS_NAME, "propertyCard", "Could not find property cards"
            )
            for card in propertyCards:
                price = getValue(
                    card,
                    By.CLASS_NAME,
                    "propertyCard-price",
                    "UNKNOWN",
                    "Could not find ADDRESS info",
                )
                address = getValue(
                    card,
                    By.CLASS_NAME,
                    "propertyCard-address",
                    "UNKNOWN",
                    "Could not find ADDRESS info",
                )
                propertyType = getValue(
                    card,
                    By.CSS_SELECTOR,
                    "div.property-information > span:nth-child(1)",
                    "UNKNOWN",
                    "Could not find PROPERTY_TYPE info",
                )
                propertyLink = getHTML(
                    card,
                    By.CSS_SELECTOR,
                    "div.propertyCard-description > a",
                    "Could not find PROPERTY_LINK info",
                ).get_attribute("href")
                bathroom = getValue(
                    driver=card,
                    by=By.CSS_SELECTOR,
                    path="div.propertyCard-details > a > div.property-information > span:nth-child(5)",
                    defaultValue="UNKNOWN",
                    errorFriendlyName="Could not find BATHROOM info",
                )
                rows.append(
                    property(
                        address=address,
                        price=price,
                        beds=0,
                        bathrooms=bathroom,
                        pictures="",
                        description="",
                        url=str(propertyLink),
                    )
                )

            if len(pagination.options) != 1:
                pagination.select_by_index(index)
        return rows
    except TimeoutException:
        print("Timed out waiting for page to load")


# url building


def build_rightmove_url(searchCriteria: criteria):
    domain = "https://www.rightmove.co.uk/property-for-sale/find.html?"
    domain += "searchType=SALE"
    domain += "&locationIdentifier=" + searchCriteria.place
    domain += "&maxPrice=" + str(searchCriteria.maxPrice)
    domain += "&minPrice=" + str(searchCriteria.minPrice)
    domain += "&minBedrooms=" + str(searchCriteria.minBed)
    domain += "&maxBedrooms=" + str(searchCriteria.maxBed)
    domain += "&newHome=" + str(searchCriteria.newHome)
    domain += "&propertyTypes=" + "%2C".join(searchCriteria.propertyTypes)
    domain += "&_includeSSTC=false&dontShow=newHome%2Cretirement%2CsharedOwnership"
    domain += "&mustHave=garden"
    domain += "&sortType=6"
    return domain


def generate_rightmove_urls(searchCriteria: criteria):
    urls = []
    for search_location in searchCriteria.locations:
        if search_location["active"] == 1:
            searchCriteria.place = search_location["code"]
            urls.append(build_rightmove_url(searchCriteria))
    return urls
