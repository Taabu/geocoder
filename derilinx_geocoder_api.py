# coding=utf-8
# __author__ = 'Mario Romera Fernández'

"""
INFORMATION
-----------
Geocoder: turn addresses in GPS coordinates
Example: Johnstown, Bennekerry, Co Carlow -> 52.82089152866102,-6.868629101436554
Datasets: Townlands__OSi_National_Placenames_Gazetteer.csv
          Counties__OSi_National_Placenames_Gazetteer.csv
Addresses to convert: addresses_for_task.csv

Programming language: Python
Version: 3.6.4

Library to handle csv: pandas
Framework for HTTP API: Flask

EXPLANATION
-----------
First of all lets have a look at the data from the datasets:
- In Counties dataset the minimum length of the counties name is 4, so anything smaller is not a valid name.
- In Townlands dataset the minimum length of the Engligh_Name is 3.
Deep looking at the English_Name column yields some more useful information, in more-than-one-word names the minimum
length of any word is 3 with just one exception: 'WOOD OF O', so no way to filter words by length.
Now lets have a look at the addresses_for_task.csv:
Some addresses are perfectly separated by commas, some aren't, some of them even have two commas together, we will have
to deal with it.
Even there are some addresses in which the special character '&' is present, if it isn't percent encoded before sending
the request it will break Flask.request.args. In command line there won't be this problem.
Addresses without commas can't be differentiate from compound names, two options arise, split them or check for
compound names.
Splitting them is the easiest but gives the poorest results because probably we won't find them, but at least we can
find the county coordinates.
Best way to deal with this situation is to check part of the address with the townlands dataset, but it will be time
and processing consuming.
The hardest part of this task would be to code a proper address parser and sanitizer.
TODO: better address parser at townlands level, even that I get at least county level coordinates this can be improved.
Once we have all the information from the address the next step is to check it against the townlads dataset.
My approach is from local to county, the first combination of elements I'm going to check are the county (last word of
the address) and the first word in the address.
If there are no positive results, next iteration is county + second word of the address, until there is only the county
name to check, in this case results will be extracted from counties dataset.
This way ensures that the first result is the most local this approach can get.
Once the coordinates are acquired, convert the data to json and send the response.

APPROACH
--------
V0 approach: input HTTP API -> csv processing and matching -> JSON response
    Step 1: function that extracts county from address
    Step 2: function that extracts coordinates from county and townland
    Step 3: HTTP API
    Step 4: test the API with the addresses provided in addresses_for_task.csv
    Cons: Not useful for large amounts of data, storing the csv in a database would be preferred
V1 approach: same as V0
    Step 1: function to handle addresses in a list of words
    Step 2: function to compare address to csv data
    Step 3: same as V0
    Step 4: same as V0
    Pros: less access to data
    Cons: still to much access to data as Step 2 must check for every element in the address
V2 approach: same as V0
    Changelog: csv reads moved to main
    Pros: execution time reduced by 200%

HOW TO RUN THE CODE
-------------------
Pre:
    Townlands__OSi_National_Placenames_Gazetteer.csv & Counties__OSi_National_Placenames_Gazetteer.csv
    must be present in the same folder as derilinx_geocoder_api.py
pyhton derilinx_geocoder_api.py
http://127.0.0.1:5000/
http://127.0.0.1:5000/api/v1/resources/addresses/?address={address}

PERFORMANCE (checked with addresses_for_task.csv)
-------------------------------------------------
CPU: Intel(R) Core(TM) i7-4700HQ CPU @ 2.40GHz
Memory: 12.0 GB DDR3 1600 MHz

V1:
Run 1:
Total addresses: 2945, local/townland level geocoding: 2720, county level geocode: 225, empty: 0
Total time: 863.3405s
Time per address: 0.2931s
Addresses per second: 3.4111 addresses/s

Run 2:
Total addresses: 2945, local/townland level geocoding: 2720, county level geocode: 225, empty: 0
Total time: 1016.7775s
Time per address: 0.3452s
Addresses per second: 2.8964 addresses/s

Run 3:
Total addresses: 2945, local/townland level geocoding: 2720, county level geocode: 225, empty: 0
Total time: 881.5760s
Time per address: 0.2993s
Addresses per second: 3.3399 addresses/s

V2:
Run 1:
Total addresses: 2945, local/townland level geocoding: 2720, county level geocode: 225, empty: 0
Total time: 48.8798s
Time per address: 0.0165s
Addresses per second: 60.2498 addresses/s

Run 2:
Total addresses: 2945, local/townland level geocoding: 2720, county level geocode: 225, empty: 0
Total time: 49.9892s
Time per address: 0.0169s
Addresses per second: 58.9127 addresses/s

Run 3:
Total addresses: 2945, local/townland level geocoding: 2720, county level geocode: 225, empty: 0
Total time: 52.1040s
Time per address: 0.0176s
Addresses per second: 56.5215 addresses/s

ADDITIONAL INFORMATION
----------------------
This is the first time I work with pandas and flask, probably there are better ways to code, faster solutions or less
cpu consuming, but I had to read (and try) the documentation of both libraries in a short amount of time so I was able
to deliver the code functional and in time.
Thank you.
"""

import flask
import pandas


app = flask.Flask(__name__)
app.config["DEBUG"] = True


def address_handler(full_address):
    """
    V1
    Separate full_address into county, townland, road and local area name
    Johnstown, Bennekerry, Co Carlow -> ['Johnstown', 'Bennekerry', 'Co', 'Carlow']
    Best way to cover every different cases stated in explanation section is:
     1 - split by commas
     2 - remove empty elements (two commas together)
     3 - remove leading spaces and dots
     4 - split by space
    :param full_address: full address input
    :return: list of str
    """

    # make a list of words split by commas
    _address_separated_list = full_address.split(',')

    # remove empty elements
    for word in _address_separated_list:
        if word == '':
            _address_separated_list.remove(word)

    # remove leading space and dots
    for index, word in enumerate(_address_separated_list):
        if word[0] == ' ':
            _address_separated_list[index] = _address_separated_list[index][1:]
        _address_separated_list[index] = _address_separated_list[index].replace('.', '')

    # check for full_address without commas and separate them
    # TODO: Improve address handler
    final_address_list = []
    for word in _address_separated_list:
        if ' ' in word:
            _aux = word.split()
            for element in _aux:
                final_address_list.append(element.upper())
        else:
            final_address_list.append(word.upper())
    return final_address_list


def extract_gps_coordinates(address_list):
    """
    V2
    Ex: ['Johnstown', 'Bennekerry', 'Co', 'Carlow']
    Compare data to csv from local to county,
    first we will try to find County 'Carlow' and English_Name 'Johnstown',
    if no results are found we will try to find County 'Carlow' and English_Name 'Bennekerry' and so on.
    This way will yield the most local result first
    :param address_list: List of str
    :return: DataFrame['County', 'English_Name', 'Y', 'X']
    """

    # match address information with townlands dataset, if no results are found on townlands dataset, match the county
    # in the county dataset
    _matched_df = pandas.DataFrame()
    while _matched_df.empty and len(address_list) >= 1:
        _matched_df = TOWNLANDS_DF.loc[(TOWNLANDS_DF['County'] == address_list[-1]) &
                                       (TOWNLANDS_DF['English_Name'] == address_list[0])]

        # if there is only one word to look for in addresses list, we look for the coordinates of the County and give
        # them as result
        if len(address_list) == 1:
            _matched_df = COUNTIES_DF.loc[COUNTIES_DF['County'] == address_list[0]]

        # remove first element
        address_list.pop(0)

    return _matched_df[['County', 'English_Name', 'Y', 'X']]  # if not _matched_df.empty else None


@app.route('/', methods=['GET'])
def home():

    return '''<h1>Derilinx Geocoder API by Mario Romera Fernández</h1>
<p>A prototype API for geocoding irish addresses.</p>
<p>Usage: <a href="http://127.0.0.1:5000/api/v1/resources/addresses?address=Johnstown, Bennekerry, Co Carlow">
http://127.0.0.1:5000/api/v1/resources/addresses/?address={address}</a>
'''


@app.errorhandler(404)
def page_not_found(e):

    return "<h1>404</h1><p>The resource could not be found.</p>", 404


@app.route('/api/v1/resources/addresses/', methods=['GET'])
def api_filter():

    # get the parameters
    query_parameters = flask.request.args

    # get the address parameter
    address = query_parameters.get('address')
    print(address)

    # split the address in words
    address_words = address_handler(address)
    print(address_words)

    # match the address against the csv
    data = extract_gps_coordinates(address_words)
    print(data)

    # convert to json and display
    return flask.jsonify(data.to_dict(orient='records'))


TOWNLANDS_CSV = 'Townlands__OSi_National_Placenames_Gazetteer.csv'
COUNTIES_CSV = 'Counties__OSi_National_Placenames_Gazetteer.csv'

# read county and townlands csv
# we need to specific 'X' and 'Y' columns dtype as 'object' so we don't lose information in the process
COUNTIES_DF = pandas.read_csv(COUNTIES_CSV, dtype={'X': 'object', 'Y': 'object'})
TOWNLANDS_DF = pandas.read_csv(TOWNLANDS_CSV, dtype={'X': 'object', 'Y': 'object'})

app.run()
