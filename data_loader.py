#   Electricity Capacity Planning Model including Air Quality Controls and
#   Health Effects [DATA_LOADER]
#
#   Author: Paul Kerl (paul.kerl@gatech.edu)
#

#imports
import random
import csv
#####################################
#########  input data  ##############
#####################################

#####################################

######### CONSTANTS #########
########    power plant types    ########
emission_types = {0 : 'OZ',
            1 : 'PM25',
            2 : 'SOX'}

pp_types = {0 : 'coal',
            1 : 'oil',
            2 : 'hydro',
            3 : 'nuclear',
            4 : 'gas',
            5 : 'biomass'}
############other sub-types required here!!!!#########

num_hours = 24 #24 hours per day
hours = list(xrange(num_hours))

num_years = 1 #number of years in horizonstarting at year ????
years = list(xrange(num_years))

num_seasons = 3; #winter, summer, intermediate
seasons = list(xrange(num_seasons))

######### END CONSTANTS #########

#####################################

######### POWER PLANTS #########

#load power plant data from CSV file into a dictionary indexed by generic plant ID

f = "data/GA_power_plants_96_09.csv"

reader = csv.DictReader(open(f), delimiter=',')

#load into a "plant_info" list
plant_info = list(reader)

#####################################

######### COSTS #########
#costs are generated from power plant type
######### POWER PLANT: START UP? COSTS #########

######### POWER PLANT: SHUT_DOWN? COSTS #########

######### POWER PLANT: VARIABLE COSTS #########

######### POWER PLANT: HEALTH COSTS per MWh #########
#these are based on the sensitivities, and are geographically dependent

######### END of COSTS #########

#####################################

######### DEMAND #########

######### DATE and HOURLY DEMAND #########

######### YEARLY TREND(s) in DEMAND #########

######### END of DEMAND #########

#####################################

######### EMISSIONS #########

######### EMISSIONS per MWh GENERATED #########

######### END of EMISSIONS #########

#####################################