import csv

def OutputCSV(rows):
    with open('houses.csv', 'w') as csvFile:
        csvWriter = csv.writer(csvFile)
        headings = ['Price', 'Address','Property Type', 'Bathrooms', 'URL']
        csvWriter.writerow(headings)
        csvWriter.writerows(rows)