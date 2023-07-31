class criteria:
    def __init__(
        self,
        place,
        searchType,
        locations,
        minBed,
        maxBed,
        minBathroom,
        maxBathroom,
        minPrice,
        maxPrice,
        newHome,
        propertyTypes,
        sort,
    ):
        self.place = place
        self.searchType = searchType
        self.locations = locations
        self.minBed = minBed
        self.maxBed = maxBed
        self.minBathroom = minBathroom
        self.maxBathroom = maxBathroom
        self.minPrice = minPrice
        self.maxPrice = maxPrice
        self.newHome = newHome
        self.propertyTypes = propertyTypes
        self.sort = sort
