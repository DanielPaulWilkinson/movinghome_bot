import random
from objects.property import property
from objects.criteria import criteria


def start_message(message):
    return (
        f"<b> Hi {message.from_user.first_name}</b> 👋 \n"
        "I'm designed to help you move home. "
        "Let's start your search right now! \n\n"
        "Currently I search for specific villages in Liverpool; Ainsdale, Formby, Ormskirk, Birkdale, Magull & Aintree. "
        "click one of the following links to begin: /find or /start_alerts \n\n"
        "Otherwise to find out more click /help where I can explain which each of my commands do."
    )


def help(message):
    return (
        f"<b>Want to know more about me? 🤖</b>\n\n"
        "▪️ <b>/find</b> - This command searches all of the villages in liverpool for properties that meet our internal criteria. 🔍\n"
        "▪️ <b>/start_alerts</b> - This command does the above but alerts you on a set 30 minute timer. ⏰\n"
        "▪️ <b>/stop_alerts</b> - This command stops me serving you new homes every 30 minutes. 💔\n"
    )


def search_message(stage, amount, location):
    rnd = random.randint(0, 6)
    stageOne = []
    stageOne.append("<b>Starting Search!</b> 🏎️")
    stageOne.append("Starting Analysis! 🧑‍💻")
    stageOne.append("Completing your orders, <b>Captain</b>! 🫡")
    stageOne.append("<b>Launching</b> Search! 🚀")
    stageOne.append("Process Initialized! 🤖")
    stageOne.append("<b>Rolling</b> Search 📹")
    stageOne.append("<b>Falling into search </b> 🎢")
    stageOne.append("<b>Altitude climb Initialized </b> 🚁")

    # checking sources  location
    stageTwo = []
    stageTwo.append("<b>Choo-Choosing Source(s)!</b> 🚄")
    stageTwo.append("Crawling! 🕷️")
    stageTwo.append("Looking at source(s)! 👀")
    stageTwo.append("Docking at ports! 🚤")
    stageTwo.append("Beginning Phase 2: searching location(s)! 🤖")
    stageTwo.append("Dodging asteroids' ☄️")
    stageTwo.append("Contacting Sources 📱")

    # processing response
    stageThree = []
    stageThree.append(
        f"<b>Snapping shots</b> of {location}! - found {amount} location(s) 📸"
    )
    stageThree.append(
        f"<b>Orbiting</b> properties in {location}! - identified {amount} location(s) 🛰️"
    )
    stageThree.append(
        f"Adjusting signal to {location}! - mapped {amount} location(s) 📡"
    )
    stageThree.append(
        f"Abducting residents of {location} - found {amount} new properties! 👽"
    )
    stageThree.append(f"Diving into {location} - found {amount} locations in chest! 🤿")
    stageThree.append(
        f"Writing down properties in {location} - made note of {amount} 🖊️"
    )
    stageThree.append(f"Searching shells in {location} - found {amount} of snacks 🐙")

    stageFour = []
    stageFour.append(f"no new properties since last search.")
    stageFour.append(f"404 properties not found.")
    stageFour.append(f"Uh oh, try search somewhere else, maybe? No properties here.")
    stageFour.append(
        f"Do not pass go, do not find a new property in the searched areas."
    )
    stageFour.append(f"I want never gets! No new properties located")
    stageFour.append(
        f"Do not pass go, do not find a new property in the searched areas."
    )
    stageFour.append(f"I want never gets! No new properties located")

    match stage:
        case 0:
            return stageOne[rnd]
        case 1:
            return stageTwo[rnd]
        case 2:
            return stageThree[rnd]
        case 3:
            return stageFour[rnd]

    return ""


def desired_bed_criteria(cri_beds, prop_beds):
    if not bool(prop_beds) or not bool(cri_beds) or str(prop_beds).lower() == "unknown":
        return "UNKNOWN"

    if int(prop_beds) >= int(cri_beds):
        return f"{prop_beds} ✅"
    elif int(prop_beds) < int(cri_beds):
        return f"{prop_beds} ❌"


def desired_bath_criteria(cri_bath, prop_bath):
    if not bool(prop_bath) or not bool(cri_bath) or str(prop_bath).lower() == "unknown":
        return ""

    if int(prop_bath) >= int(cri_bath):
        return f"{prop_bath} ✅"
    elif int(prop_bath) < int(cri_bath):
        return f"{prop_bath} ❌"


def property_message(p: property, c: criteria):
    return (
        f"<b>Price</b>: {p.price}"
        f"<b>Location</b>: <a href='https://www.google.co.uk/maps/place/{p.address}'>{p.address}</a> \n"
        f"<b>Bed Count</b>: {desired_bed_criteria(c.minBed ,p.beds)} \n"
        f"<b>Bathroom Count</b>: {desired_bath_criteria(c.minBathroom, p.bathrooms)} \n"
        f"<a href='{p.url}'>Click here</a> to view!"
    )
