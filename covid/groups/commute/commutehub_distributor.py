import numpy as np
from scipy import spatial


class CommuteHubDistributor:
    """
    Distribute people to commute hubs based on where they live and where they are commuting to
    """

    def __init__(self, oa_coordinates, commutecities):
        """
        oa_coordinates: (pd.Dataframe) Dataframe of all OA postcodes and lat/lon coordinates
        commutecities: (list) members of CommuteCities
        """
        self.oa_coordinates = oa_coordinates
        self.commutecities = commutecities

    def _get_area_lat_lon(self, oa):
        lat = float(self.oa_coordinates['Y'][self.oa_coordinates['OA11CD'] == oa])
        lon = float(self.oa_coordinates['X'][self.oa_coordinates['OA11CD'] == oa])

        return [lat,lon]

    def distirbute_people(self):

        for commutecity in self.commutecities:
            # people commuting into city
            work_people = commutecity.passengers

            # possible commutehubs
            commutehub_in_city = commutecity.commutehubs
            commutehub_in_city_lat_lon = []
            for commutehub in commutehub_in_city:
                commutehub_in_city_lat_lon.append(commuthub.lat_lon)

            for work_person in work_people:
                # check if live AND work in metropolitan area
                if work_person.msoarea in commutecity.metro_msoas:
                    pass

                # if they live outside and commute in then they need to commute through a hub
                else:
                    live_area = work_person.area
                    live_lat_lon = self._get_area_lat_lon(live_area)
                    # find nearest commute hub to the person given where they live
                    _, hub_index = spatial.KDTree(commutehub_in_city).query(live_lat_lon,1)

                    commutehub_in_city[hub_index].passengers.append(work_person)
                    
                    
                    
