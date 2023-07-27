import json

def get_config():
    with open("Data/config.json", "r") as read_file:
        return json.load(read_file)["config"]

def GetData(filename: str = "Data/data_file.json", defaultValue: str = ""):
    with open(filename, "r") as read_file:
        try:
            read = json.load(read_file)
            read_file.close()
            return read
        except:
            return defaultValue 

def HasUserBeenAlertedToNewProperty(url: str):
    data = GetData()
    if not bool(data):
        return 0
    for i in data["p"]:
        if(i["url"] == url):
            return 1
    return 0

def AppendToFile(url: str):
    try:
        data = []
        
        with open("Data/data_file.json", "r") as rf:
            data = json.load(rf)
            rf.close()
        with open("Data/data_file.json", "w") as wf:
            data["p"].append({"url":str(url)})
            json.dump(data, wf, indent=4, separators=(',',': '))  
            wf.close()
    except Exception as inst:
        print(inst)



