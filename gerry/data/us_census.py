"""
Routines for downloading data from the US Census Bureau. Currently
only some of the redistricting data has been experimented with.

Functions
---------
_merge_dataframe_shapefile(df, gdf)
    Merges the dataframe and geodataframe into a single geodataframe,
    joining on the column `GEOID`.

_parse_state(state)
    Checks to see whether the input is a us.state.State object
    or is a recognizable state from the input string using the 
    us.states.lookup method.

get_block_groups(survey, state, fields, year, redownload, save)
    Returns a GeoDataFrame containing the attribute information
    from the indiciated survey along the shapefile information
    at the block group level.

get_counties(survey, state, fields, year, redownload, save)
    Returns a GeoDataFrame containing the attribute information
    from the indiciated survey along the shapefile information
    at the county level.

get_tracts(survey, state, fields, year, redownload, save)
    Returns a GeoDataFrame containing the attribute information
    from the indiciated survey along the shapefile information
    at the tract level.

Classes
-------
SurveyData
    Class used for saving and loading survey data. Mainly used
    to prevent having to re-download data.

TigerShapefile
    Class for retrieving shapefiles associated with various geographical
    units from the US Census Bureau. Used to store files rather than
    download them at each call.
"""
import census
import geopandas
import os
import pandas
import requests
import us
from typing import List, Union

def _merge_dataframe_shapefile(df:pandas.DataFrame, gdf:geopandas.GeoDataFrame) -> geopandas.GeoDataFrame:
    """
    Merges the dataframe and geodataframe into a single geodataframe,
    joining on the column `GEOID`.

    Parameters
    ----------
    df : pandas.DataFrame
        The dataframe containing attribute information.

    gdf : geopandas.GeoDataFrame
        The geodataframe containing the shapefile data.
    
    Returns
    -------
    geodata : geopandas.GeoDataFrame
        A geodataframe containing the merged information.
    """
    return gdf.merge(df, on='GEOID')

def _parse_state(state:Union[str,us.states.State], **kwargs) -> us.states.State:
    """
    Checks to see whether the input is a us.state.State object
    or is a recognizable state from the input string using the 
    us.states.lookup method.

    Parameters
    ----------
    state : str, us.states.State
        A state identifier.

    **kwargs
        Additional arguments to pass into the us.states.lookup
        method.
    
    Returns
    -------
    state : us.states.State
        A us.states.State representation of the state.

    Raises
    ------
    ValueError
        If the us.states.lookup function fails to identify an associated
        state, then a ValueError is raised.

        If the input is not a string or a us.states.State object, then
        a ValueError is raised.
    """
    if isinstance(state, str):
        state = us.states.lookup(state, **kwargs)
        if state is None:
            raise ValueError("Argument `{state}` not recognized as a valid state")
        return state
    elif isinstance(state, us.states.State):
        return state
    else:
        raise ValueError("Argument `state` must be either a string or a us.states.State object")

class TigerShapefile:
    """
    Class for retrieving shapefiles associated with various geographical
    units from the US Census Bureau. Used to store files rather than
    download them at each call.

    Attributes
    ----------
    state : us.states.State
        The state identifier.

    geounit : str
        The geographical unit representation. The available options can be
        found at: https://www2.census.gov/geo/tiger/TIGER2020/

    year: int
        The associated year to use for extracting the shapefiles.

    us_only : List[str]
        A list of identifiers for geographical units that are only represented
        at the National level and lack a unique shapefile for each state.

    Methods
    -------
    download()
        Downloads the TIGER/Line shapefile products and stores them locally.

    load()
        If the shapefiles have previously been downloaded, then they are
        loaded and returned as a GeoDataFrame. Otherwise, the files are
        downloaded and then returned.

    Properties
    ----------
    dir : str
        The directory where the shapefile is stored.
    
    filename : str
        The name of the shapefile.
    
    filepath : str
        The path to the shapefile object.

    url : str
        The url path associated with the shapefile. 
    """
    def __init__(self, 
        state:Union[str, us.states.State],
        geounit:str='bg',
        year:int=2020,
        us_only:List[str]=['county']
    ):
        """
        Parameters
        ----------
        state : str, us.states.State
            The state identifier.

        geounit : str
            The geographical unit representation. The available options can be
            found at: https://www2.census.gov/geo/tiger/TIGER2020/

        year: int
            The associated year to use for extracting the shapefiles.

        us_only : List[str]
            A list of identifiers for geographical units that are only represented
            at the National level and lack a unique shapefile for each state.
        """
        self.state = _parse_state(state)
        self.geounit = geounit.lower()
        self.year = year
        self.us_only = us_only

    def download(self):
        """
        Downloads the TIGER/Line shapefile products and stores them locally.
        """
        r = requests.get(self.url) 
        if not os.path.exists(self.dir):
            os.makedirs(self.dir)
        with open(self.filepath, 'wb') as f:
            f.write(r.content)        

    def load(self):
        """
        If the shapefiles have previously been downloaded, then they are
        loaded and returned as a GeoDataFrame. Otherwise, the files are
        downloaded and then returned.
        """
        if os.path.exists(self.filepath):
            return geopandas.read_file(self.filepath)
        else:
            self.download()
            return self.load()

    @property
    def dir(self):
        path = os.path.join(os.path.dirname(__file__), 'files')
        if self.geounit not in self.us_only:
            path = os.path.join(path, self.state.abbr)
        return path

    @property
    def filename(self):
        if self.geounit in self.us_only:
            return f"tl_{self.year}_us_{self.geounit.lower()}.zip"
        else:
            return f"tl_{self.year}_{self.state.fips}_{self.geounit.lower()}.zip"

    @property
    def filepath(self):
        return os.path.join(self.dir, self.filename)

    @property
    def url(self):
        return f"https://www2.census.gov/geo/tiger/TIGER{self.year}/{self.geounit.upper()}/{self.filename}"
 
class SurveyData:
    """
    Class used for saving and loading survey data. Mainly used
    to prevent having to re-download data.

    Attributes
    ----------
    dataset : str
        A string representing the survey the data is extracted from.

    geounit : str
        The geographical unit representation. The available options can be
        found at: https://www2.census.gov/geo/tiger/TIGER2020/

    state : us.states.State
        The state identifier.

    Methods
    -------
    check_exists()
        Returns a boolean indicating whether the file exists.

    load()
        Loads and returns the stored file.

    save(df)
        Saves the provided dataframe.

    Properties
    ----------
    dir : str
        The directory where the dataframe is stored.

    filename : str
        The name of the saved dataframe.
    
    filepath : str
        The path to the saved dataframe.
    """
    def __init__(self,
        survey:census.core.Client,
        state:Union[str,us.states.State],
        geounit:str
    ):
        """
        Parameters
        ----------
        survey : census.core.client
            The survey the data is extracted from.

        state : str, us.states.State
            The state identifier.

        geounit : str
            The geographical unit representation. The available options can be
            found at: https://www2.census.gov/geo/tiger/TIGER2020/
        """
        self.state = _parse_state(state)
        self.dataset = survey.dataset
        self.geounit = geounit

    @property
    def dir(self) -> str:
        return os.path.join(os.path.dirname(__file__), 'files', self.state.abbr)

    @property
    def filename(self) -> str:
        return f"{self.state.abbr}_{self.dataset}_{self.geounit}.pkl"

    @property
    def filepath(self) -> str:
        return os.path.join(self.dir, self.filename)

    def check_exists(self) -> bool:
        """
        Returns a boolean indicating whether the file exists.
        """
        return True if os.path.exists(self.filepath) else False

    def load(self) -> pandas.DataFrame:
        """
        Loads and returns the stored file.
        """
        return pandas.read_pickle(self.filepath)

    def save(self, df:pandas.DataFrame) -> None:
        """
        Saves the provided dataframe.
        """
        df.to_pickle(self.filepath)

def get_block_groups(
    survey:census.core.Client,
    state:Union[str,us.states.State],
    fields:Union[str, List[str]],
    year:int=2020,
    redownload:bool=True,
    save:bool=False,
) -> geopandas.GeoDataFrame:
    """
    Returns a GeoDataFrame containing the attribute information
    from the indiciated survey along the shapefile information
    at the block group level.

    Parameters
    ----------
    survey : census.core.Client
        The survey to retrieve the data from.

    state : str, us.states.State
        The state identifier.

    fields : str, List[str]
        The field identifier, or a set of such identifiers, to
        extract from the survey.

    year : int
        The associated year to use for extracting the shapefiles.

    redownload : bool
        Boolean indicating whether to re-download the survey data
        (True) or to reload the stored data (False) if the previous
        query was saved. If using a new set of fields, then it
        should be set to True.

    save : bool
        Boolean indicating whether to save the survey data if it
        is downloaded.

    Examples
    --------
    import matplotlib.pyplot as plt
    from census import Census
    from gerry.data.us_census import get_block_groups

    api_key = open("census_api_key.txt").readline()    # Path to api_key
    field = 'P1_001N'
    gdf = get_block_groups(
        survey = Census(api_key).pl,    # Redistricting survey
        state = 'Iowa',
        fields = field,                 # Total population
    )
    
    fig, ax = plt.subplots()
    gdf.plot(column=field, ax=ax)
    fig.show()
    """
    gdf = TigerShapefile(state, geounit='bg', year=year).load()
    sd  = SurveyData(survey, state, geounit='bg')
    if sd.check_exists() and (not redownload):
        df = sd.load()
    else:
        df = pandas.DataFrame(survey.state_county_blockgroup(
            fields=fields,
            state_fips=_parse_state(state).fips,
            county_fips=census.Census.ALL,
            blockgroup=census.Census.ALL,
        ))
        if save: 
            sd.save(df)

    df['GEOID'] = df['state'] + df['county'] + df['tract'] + df['block group']
    return _merge_dataframe_shapefile(df=df, gdf=gdf)

def get_counties(
    survey:census.core.Client,
    state:Union[str,us.states.State],
    fields:Union[str, List[str]],
    year:int=2020,
    redownload:bool=True,
    save:bool=False,
) -> geopandas.GeoDataFrame:
    """
    Returns a GeoDataFrame containing the attribute information
    from the indiciated survey along the shapefile information
    at the county level.

    Parameters
    ----------
    survey : census.core.Client
        The survey to retrieve the data from.

    state : str, us.states.State
        The state identifier.

    fields : str, List[str]
        The field identifier, or a set of such identifiers, to
        extract from the survey.

    year : int
        The associated year to use for extracting the shapefiles.

    redownload : bool
        Boolean indicating whether to re-download the survey data
        (True) or to reload the stored data (False) if the previous
        query was saved. If using a new set of fields, then it
        should be set to True.

    save : bool
        Boolean indicating whether to save the survey data if it
        is downloaded.


    Examples
    --------
    import matplotlib.pyplot as plt
    from census import Census
    from gerry.data.us_census import get_counties

    api_key = open("census_api_key.txt").readline()    # Path to api_key
    field = 'P1_001N'
    gdf = get_counties(
        survey = Census(api_key).pl,    # Redistricting survey
        state = 'Iowa',
        fields = field,                 # Total population
    )
    
    fig, ax = plt.subplots()
    gdf.plot(column=field, ax=ax)
    fig.show()
    """
    state = _parse_state(state)
    gdf = TigerShapefile(state, geounit='county', year=year).load()
    gdf = gdf.loc[gdf.STATEFP == str(state.fips), :]   # Keep only the relevant states
    sd  = SurveyData(survey, state, geounit='county')
    if sd.check_exists() and (not redownload):
        df = sd.load()
    else:
        df = pandas.DataFrame(survey.state_county(
            fields=fields,
            state_fips=state.fips,
            county_fips=census.Census.ALL,
        ))
        if save:
            sd.save(df)

    df['GEOID'] = df['state'] + df['county']
    return _merge_dataframe_shapefile(df=df, gdf=gdf)  

def get_tracts(
    survey:census.core.Client,
    state:Union[str,us.states.State],
    fields:Union[str, List[str]],
    year:int=2020,
    redownload:bool=True,
    save:bool=False,
) -> geopandas.GeoDataFrame:
    """
    Returns a GeoDataFrame containing the attribute information
    from the indiciated survey along the shapefile information
    at the tract level.

    Parameters
    ----------
    survey : census.core.Client
        The survey to retrieve the data from.

    state : str, us.states.State
        The state identifier.

    fields : str, List[str]
        The field identifier, or a set of such identifiers, to
        extract from the survey.

    year : int
        The associated year to use for extracting the shapefiles.

    redownload : bool
        Boolean indicating whether to re-download the survey data
        (True) or to reload the stored data (False) if the previous
        query was saved. If using a new set of fields, then it
        should be set to True.

    save : bool
        Boolean indicating whether to save the survey data if it
        is downloaded.

    Examples
    --------
    import matplotlib.pyplot as plt
    from census import Census
    from gerry.data.us_census import get_tracts

    api_key = open("census_api_key.txt").readline()    # Path to api_key
    field = 'P1_001N'
    gdf = get_tracts(
        survey = Census(api_key).pl,    # Redistricting survey
        state = 'Iowa',
        fields = field,                 # Total population
    )
    
    fig, ax = plt.subplots()
    gdf.plot(column=field, ax=ax)
    fig.show()
    """
    gdf = TigerShapefile(state, geounit='tract', year=year).load()
    sd  = SurveyData(survey, state, geounit='tract')
    if sd.check_exists() and (not redownload):
        df = sd.load()
    else:
        df = pandas.DataFrame(survey.state_county_tract(
            fields=fields,
            state_fips=_parse_state(state).fips,
            county_fips=census.Census.ALL,
            tract=census.Census.ALL,
        ))
        if save:
            sd.save(df)

    df['GEOID'] = df['state'] + df['county'] + df['tract']
    return _merge_dataframe_shapefile(df=df, gdf=gdf)
