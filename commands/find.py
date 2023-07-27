from telegram import Update
from telegram.ext import ContextTypes
import Services.RightmoveService as RightmoveService
import Services.JsonService as JsonService
import Services.DriverService as DriverService

async def find_properties_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    minBed = 3
    maxBed = 3
    minBathroom = 1
    maxBathroom = 2
    minPrice = 150000
    maxPrice = 250000
    newHome = 0
    place = 'Formby'
    propertyTypes = ['bungalow', 'detached', 'semi-detached','terraced']
    locationsRightMove = {'Aintree':'REGION%5E1749','Formby':'REGION%5E10170', 'Ainsdale':'REGION%5E1745'}
    sort ='newest'
    searchType = 'sale'
    searchCriteria = RightmoveService.Criteria(place=place, searchType=searchType, locations=locationsRightMove,minBed=minBed,maxBed=maxBed,minBathroom=minBathroom, maxBathroom=maxBathroom, minPrice=minPrice, maxPrice=maxPrice, newHome=newHome,propertyTypes=propertyTypes,sort=sort)
    urls = RightmoveService.GenerateURLsFromCriteria(searchCriteria)
    await update.message.reply_text('Checking for new properties')
    
    properties = []

    driver = DriverService.Create()

    properties.extend(RightmoveService.GetRightMoveProperties(driver, urls['RightMoveFormby']))
    properties.extend(RightmoveService.GetRightMoveProperties(driver, urls['RightMoveAintree']))
    properties.extend(RightmoveService.GetRightMoveProperties(driver, urls['RightMoveAinsdale']))
    
    propertiesToRemove = []
    propertiesToShow = []
    for property in properties:
        alerted = JsonService.HasUserBeenAlertedToNewProperty(property[4])
        if(alerted == 1):
            propertiesToRemove.append(property)
        else:
            propertiesToShow.append(property)
            JsonService.AppendToFile(property[4])
            print("Bot:", "appended to file" + property[4])
        
    if(len(propertiesToShow) == 0):
        await update.message.reply_text('Aw, no new properties have been found for your criteria :(')
        return
    else:
        for property in propertiesToShow:
            stringLimit = '\n'
            text = (f"Price: {property[0].split(stringLimit)[0]}\ - Location: {property[1]}\ - View More:{property[4]}")
            await update.message.reply_text(text)
                     
async def find_callback(context):
    chat_id = context.job.chat_id
    minBed = 3
    maxBed = 3
    minBathroom = 1
    maxBathroom = 2
    minPrice = 150000
    maxPrice = 250000
    newHome = 0
    place = 'Formby'
    propertyTypes = ['bungalow', 'detached', 'semi-detached']
    locationsRightMove = {'Aintree':'REGION%5E1749','Formby':'REGION%5E10170', 'Ainsdale':'REGION%5E1745'}
    sort ='newest'
    searchType = 'sale'
    searchCriteria = RightmoveService.Criteria(place=place, searchType=searchType, locations=locationsRightMove,minBed=minBed,maxBed=maxBed,minBathroom=minBathroom, maxBathroom=maxBathroom, minPrice=minPrice, maxPrice=maxPrice, newHome=newHome,propertyTypes=propertyTypes,sort=sort)
    urls = RightmoveService.GenerateURLsFromCriteria(searchCriteria)    
    properties = []
    driver = DriverService.Create()
    properties.extend(RightmoveService.GetRightMoveProperties(driver, urls['RightMoveFormby']))
    properties.extend(RightmoveService.GetRightMoveProperties(driver, urls['RightMoveAintree']))
    properties.extend(RightmoveService.GetRightMoveProperties(driver, urls['RightMoveAinsdale']))
    propertiesToRemove = []
    propertiesToShow = []
    for property in properties:
        #check if warned user already (by checking json for id)
        alerted = JsonService.HasUserBeenAlertedToNewProperty(property[4])
        #if json contains id remove this property from the list
        if(alerted == 1):
            propertiesToRemove.append(property)
        else:
            propertiesToShow.append(property)
            JsonService.AppendToFile(property[4])
    if(len(propertiesToShow) == 0):
        return
    else:
        for property in propertiesToShow:
            stringLimit = '\n'
            text = (f"Price: {property[0].split(stringLimit)[0]}{stringLimit}Location: {property[1]}{stringLimit}View More:{property[4]}")
            await context.bot.send_message(chat_id=chat_id, text=text)