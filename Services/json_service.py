import json
import os
from objects.criteria import criteria
from objects.property import property

"""
    Get the application config
    returns bot name, bot token, data paths  
"""


def get_application_config():
    with open("data/config.json", "r") as read_file:
        return json.load(read_file)["config"]


"""
    Gets all property data from the JSON file
    returns JSON data of all properties    
"""


def get_property_data():
    config = get_application_config()
    path = config["properties_json"]

    if os.stat(path).st_size == 0:
        return ""
    else:
        with open(path, "r") as data:
            fileData = json.load(data)
            data.close()
            return fileData


def check_duplicate_property_exists(p: property):
    path = get_application_config()["properties_json"]
    create_base_json = {"p": []}

    if os.stat(path).st_size == 0:
        with open(path, "w") as wf:
            json.dump(create_base_json, wf, indent=4, separators=(",", ": "))
            wf.close()

    data = get_property_data()
    for property in data["p"]:
        if property["url"] == p.url and property["price"] == p.price:
            return 1
    return 0


def update_property_price_history(url: str, price: str, newPrice: str):
    path = get_application_config()["properties_json"]
    create_base_json = {"p": []}
    if os.stat(path).st_size == 0:
        with open(path, "w") as wf:
            json.dump(create_base_json, wf, indent=4, separators=(",", ": "))
            wf.close()

    with open(path, "r") as rf:
        data = json.load(rf)
        rf.close()

    prop

    if "p" in data:
        for property in data["p"]:
            if property["url"] == url:
                prop = property
                break

    create_history = f'"history": [{"id": 1, "price": newPrice}]'
    if not "history" in prop:
        prop.append(create_history)
    else:
        length = len(prop["History"])
        prop["history"].append({"id": length + 1, "price": newPrice})

    with open("Data/data_file.json", "w") as wf:
        json.dump(data, wf, indent=4, separators=(",", ": "))
        wf.close()


def add_property_to_json(p: property):
    path = get_application_config()["properties_json"]
    create_base_json = {"p": []}
    if os.stat(path).st_size == 0:
        with open(path, "w") as wf:
            json.dump(create_base_json, wf, indent=4, separators=(",", ": "))
            wf.close()

    try:
        data = []

        with open(path, "r") as rf:
            data = json.load(rf)
            rf.close()
        with open(path, "w") as wf:
            data["p"].append({"url": str(p.url), "price": str(p.price)})
            json.dump(data, wf, indent=4, separators=(",", ": "))
            wf.close()
    except Exception as inst:
        print(inst)


def get_search_criteria() -> criteria:
    path = get_application_config()["search_criteria_json"]
    with open(path, "r") as data:
        c = json.load(data)["rightmove"]["criteria"]
        return criteria(
            "",
            c["searchType"],
            c["locations"],
            c["minBed"],
            c["maxBed"],
            c["minBathroom"],
            c["maxBathroom"],
            c["minPrice"],
            c["maxPrice"],
            c["newHome"],
            c["propertyTypes"],
            c["sort"],
        )
