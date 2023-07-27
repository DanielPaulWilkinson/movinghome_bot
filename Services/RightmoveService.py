
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from Objects.SearchCriteria import Criteria
from Services.DriverService import *
 
#scraping methods
def GetRightMoveProperties(drive: webdriver, url: str):
    rows = [];
    try:        
        driver = goto(drive,url)
        waitForPageLoad(driver)
        pagination = CreateSelect(driver,By.CLASS_NAME,'pagination-dropdown', 'Could not find pagination')
        for index in range(len(pagination.options)):
            propertyCards =  getHTMLGroups(driver, By.CLASS_NAME,'propertyCard', 'Could not find property cards')
            for card in propertyCards:                 
                price = getValue(card,By.CLASS_NAME,'propertyCard-price', 'UNKNOWN', 'Could not find ADDRESS info')                                                                                                     
                address = getValue(card,By.CLASS_NAME,'propertyCard-address', 'UNKNOWN', 'Could not find ADDRESS info')
                propertyType = getValue(card,By.CSS_SELECTOR,'div.property-information > span:nth-child(1)', 'UNKNOWN', 'Could not find PROPERTY_TYPE info')
                propertyLink =  getHTML(card,By.CSS_SELECTOR,'div.propertyCard-description > a', 'Could not find PROPERTY_LINK info').get_attribute('href')
                bathroom = getValue(card,By.CSS_SELECTOR,'div.propertyCard-details > a > div.property-information > span:nth-child(5)', 'UNKNOWN', 'Could not find BATHROOM info')
                rows.append([price, address, propertyType, bathroom, propertyLink])
            if(len(pagination.options) != 1):
                pagination.select_by_index(index)
        return rows      
    except TimeoutException:
        print("Timed out waiting for page to load")
        
def GetZooplaProperties(url):
    rows = [];
    try:        
        driver = goto(url)
        waitForPageLoad(driver)
        print(driver)
        propertyCards =  getHTMLGroups(driver, By.XPATH,"//div[starts-with(@id, 'listing_')]", 'Could not find property cards')
        print(propertyCards.text.strip())
        for card in propertyCards:                 
            price = getValue(card,By.CLASS_NAME,'propertyCard-price', 'UNKNOWN', 'Could not find ADDRESS info')                                                                                                     
            address = getValue(card,By.CLASS_NAME,'propertyCard-address', 'UNKNOWN', 'Could not find ADDRESS info')
            propertyType = getValue(card,By.CSS_SELECTOR,'div.property-information > span:nth-child(1)', 'UNKNOWN', 'Could not find PROPERTY_TYPE info')
            propertyLink =  getHTML(card,By.CSS_SELECTOR,'div.propertyCard-description > a', 'Could not find PROPERTY_LINK info').get_attribute('href')
            bathroom = getValue(card,By.CSS_SELECTOR,'div.propertyCard-details > a > div.property-information > span:nth-child(5)', 'UNKNOWN', 'Could not find BATHROOM info')
            rows.append({'price': price, 'address':address, 'propertyType': propertyType, 'bathroom': bathroom, 'url':propertyLink})
        return rows
    except TimeoutException:
        print("Timed out waiting for page to load")
    
#url building
def BuildRightMoveUrl(searchCriteria: Criteria):

    domain = 'https://www.rightmove.co.uk/property-for-sale/find.html?'
    
    if (searchCriteria.searchType == 'sale'):
        domain +='searchType=SALE'
    
    match searchCriteria.place:    
        case 'Aintree':
            domain += '&locationIdentifier=' + searchCriteria.locations.get('Aintree')
        case 'Formby':
            domain += '&locationIdentifier=' + searchCriteria.locations.get('Formby')
        case 'Ainsdale':
            domain += '&locationIdentifier=' + searchCriteria.locations.get('Ainsdale')

    domain += '&maxPrice=' + str(searchCriteria.maxPrice)
    domain += '&minPrice=' + str(searchCriteria.minPrice)
    domain += '&minBedrooms=' + str(searchCriteria.minBed)
    domain += '&maxBedrooms=' + str(searchCriteria.maxBed)
    domain += '&newHome=' + str(searchCriteria.newHome)
    domain += '&propertyTypes=' + '%2C'.join(searchCriteria.propertyTypes)
    domain += '&_includeSSTC=false&dontShow=newHome%2Cretirement%2CsharedOwnership'
    domain += '&mustHave=garden'
    domain += '&sortType=6'
    
    return domain

def buildZooplaUrl(searchCriteria: Criteria):
    domain = 'https://www.zoopla.co.uk/for-sale/houses'
    
    domain += '/{beds}-bedrooms'.format(beds=searchCriteria.maxBed)
    domain += '/' + str(searchCriteria.place) + '/?'

    domain += 'price_max=' + str(searchCriteria.maxPrice)
    domain += '&price_min=' + str(searchCriteria.minPrice)
    
    for sub_type in searchCriteria.propertyTypes:
        domain += '&property_sub_type=' + sub_type

    domain += '&q=' + searchCriteria.place

    if (searchCriteria.searchType == 'sale'):
        domain += '&search_source=' + 'for-sale'
        
    return domain

def GenerateURLsFromCriteria(searchCriteria: Criteria):
    
    urls = {
        'Zoopla':buildZooplaUrl(searchCriteria),
        'RightMoveFormby': "",
        'RightMoveAintree': "",
        'RightMoveAinsdale': ""
    }
        
    for i in searchCriteria.locations:
        match i:
            case "Formby":
                searchCriteria.place = i
                urls['RightMoveFormby'] = BuildRightMoveUrl(searchCriteria)
            case "Aintree":
                searchCriteria.place = i
                urls['RightMoveAintree'] = BuildRightMoveUrl(searchCriteria)
            case "Ainsdale":
                searchCriteria.place = i
                urls['RightMoveAinsdale'] = BuildRightMoveUrl(searchCriteria)
 
    
    return urls
    
    

    


            


