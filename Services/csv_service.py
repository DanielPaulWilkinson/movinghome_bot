import csv


def generate_csv(rows):
    with open("houses.csv", "w") as csvFile:
        csvWriter = csv.writer(csvFile)
        headings = ["Price", "Address", "Property Type", "Bathrooms", "URL"]
        csvWriter.writerow(headings)
        csvWriter.writerows(rows)
        csvFile.close()
