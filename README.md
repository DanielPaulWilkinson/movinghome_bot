# movinghome_bot
This bot crawls rightmove.co.uk and scrapes the property data from particular places that I've specified in a hardcoded way at the moment. Currently this excludes new builds and returns the data sorted by newest listed. We're looking for a 3 bed, 1 bathroom house with a garden in particular villages in liverpool. All results are shown in the form of a telegram chat. 

# setup
You will need to add a JSON file at Data/config.json with the following JSON
{
"name" - "name of the bot"
"token" - "given by the @botfather"
}

then you can run "python movinghome_bot.py" and this should begin the scrape. 

# Features
1) Has a range of commands which pop up on mobile and desktop telegram apps. ![commands](https://github.com/DanielPaulWilkinson/movinghome_bot/assets/29014077/81a82fe0-b964-4872-8ff9-c8ba1d8c99b2)
2) Manually type '/find' into the bot chat window and a crawler will search for properties in liverpool.![find](https://github.com/DanielPaulWilkinson/movinghome_bot/assets/29014077/c18e0c96-3c79-439f-90c1-1de8f732dde8) 
3) Set auto alerts every 30 minutes for properties and turn them off. ![alerts](https://github.com/DanielPaulWilkinson/movinghome_bot/assets/29014077/b7a0d2b5-9985-49f2-953c-cd532aca5994)
3) Will show property once and then add to a black list file data_file.json

Future Improvements Suggested:
1) Make this user or chat_id specific - will need a better way of storing data.
2) Custom locations
3) A way of not scraping the same data twice
4) A way of scraping data from added locations easily.
5) A way of adding to black list but showing if the data scraped is different such as if price is reduced for the property. 


