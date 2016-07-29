# Time to put in proper comments overywher
from __future__ import absolute_import

import logging
# import re
from itertools import chain, imap

# import requests
from .utilities import f2i
from pgoapi.rpc_api import RpcApi
from pgoapi.auth_ptc import AuthPtc
from pgoapi.auth_google import AuthGoogle
from pgoapi.exceptions import AuthException, ServerBusyOrOfflineException
# from termcolor import colored # get color logging soon
from pgoapi.protos.POGOProtos.Networking.Requests_pb2 import RequestType
from pgoapi.protos.POGOProtos import Inventory_pb2 as Inventory

import pickle
import random
import json
from pgoapi.location import distance_in_meters, get_increments, get_neighbors, get_route, filtered_forts
# import pgoapi.protos.POGOProtos.Enums_pb2 as RpcEnum
from pgoapi.poke_utils import pokemon_iv_percentage, get_inventory_data, get_pokemon_num, get_incubators_stat
from time import sleep
from collections import defaultdict
import os.path

logger = logging.getLogger(__name__)

# Candy needed to evolve pokemon  to add new pokemon to auto evolve list edit them here
CANDY_NEEDED_TO_EVOLVE = {1: 24,  # Bulbasaur
                          2: 99,  # Ivysaur
                          4: 24,  # Charmander
                          5: 99,  # Charmeleon
                          7: 24,  # Squirtle
                          8: 99,  # Wartortle
                          10: 11,  # Caterpie
                          11: 49,  # Metapod
                          13: 11,  # Weedle
                          14: 49,  # Kakuna
                          16: 11,  # Pidgey
                          17: 49,  # Pidgeotto
                          19: 24,  # Rattata
                          21: 49,  # Spearow
                          23: 49,  # Ekans
                          25: 49,
                          27: 49,
                          29: 24,
                          30: 99,
                          32: 24,
                          33: 99,
                          35: 49,
                          37: 49,
                          39: 50,
                          41: 44,
                          43: 24,
                          44: 99,
                          46: 49,
                          48: 49,
                          50: 49,
                          52: 49,
                          54: 49,
                          56: 49,
                          58: 49,
                          60: 24,  # Poliwag
                          61: 99,
                          63: 24,
                          64: 99,
                          66: 24,
                          67: 99,
                          69: 24,
                          70: 99,
                          72: 49,
                          74: 24,
                          75: 99,
                          77: 49,
                          79: 49,
                          81: 49,
                          84: 49,
                          86: 49,
                          88: 49,
                          90: 49,  # Shellder
                          92: 24,
                          93: 99,
                          96: 49,  # Drowzee
                          98: 49,
                          100: 49,
                          102: 49,
                          104: 49,
                          109: 49,
                          111: 49,
                          116: 49,
                          118: 49,
                          120: 49,
                          129: 399,
                          133: 24,
                          138: 49,
                          140: 49,
                          147: 24,
                          148: 99}

POKEBALLS = ["Pokeball", "Great Ball", "Ultra Ball", "Master Ball"]  # you only get one master ball dont waste it botting

MIN_SIMILAR_POKEMON = 1  # change this to keep more doubles if you have release duplicates set to ture

INVENTORY_DICT = {Inventory.ITEM_UNKNOWN: "UNKNOWN",
                  Inventory.ITEM_POKE_BALL: "POKE_BALL",
                  Inventory.ITEM_GREAT_BALL: "GREAT_BALL",
                  Inventory.ITEM_ULTRA_BALL: "ULTRA_BALL",
                  Inventory.ITEM_MASTER_BALL: "MASTER_BALL",
                  Inventory.ITEM_POTION: "POTION",
                  Inventory.ITEM_SUPER_POTION: "SUPER_POTION",
                  Inventory.ITEM_HYPER_POTION: "HYPER_POTION",
                  Inventory.ITEM_MAX_POTION: "MAX_POTION",
                  Inventory.ITEM_REVIVE: "REVIVE",
                  Inventory.ITEM_MAX_REVIVE: "MAX_REVIVE",
                  Inventory.ITEM_LUCKY_EGG: "LUCKY_EGG",
                  Inventory.ITEM_INCENSE_ORDINARY: "INCENSE_ORDINARY",
                  Inventory.ITEM_INCENSE_SPICY: "INCENSE_SPICY",
                  Inventory.ITEM_INCENSE_COOL: "INCENSE_COOL",
                  Inventory.ITEM_INCENSE_FLORAL: "INCENSE_FLORAL",
                  Inventory.ITEM_TROY_DISK: "TROY_DISK/LURE_MODULE",
                  Inventory.ITEM_X_ATTACK: "X_ATTACK",
                  Inventory.ITEM_X_DEFENSE: "X_DEFENSE",
                  Inventory.ITEM_X_MIRACLE: "X_MIRACLE",
                  Inventory.ITEM_RAZZ_BERRY: "RAZZ_BERRY",
                  Inventory.ITEM_BLUK_BERRY: "BLUK_BERRY",
                  Inventory.ITEM_NANAB_BERRY: "NANAB_BERRY",
                  Inventory.ITEM_WEPAR_BERRY: "WEPAR_BERRY",
                  Inventory.ITEM_PINAP_BERRY: "PINAP_BERRY",
                  Inventory.ITEM_SPECIAL_CAMERA: "SPECIAL_CAMERA",
                  Inventory.ITEM_INCUBATOR_BASIC_UNLIMITED: "INCUBATOR_BASIC_UNLIMITED",
                  Inventory.ITEM_INCUBATOR_BASIC: "INCUBATOR_BASIC",
                  Inventory.ITEM_POKEMON_STORAGE_UPGRADE: "POKEMON_STORAGE_UPGRADE",
                  Inventory.ITEM_ITEM_STORAGE_UPGRADE: "ITEM_STORAGE_UPGRADE"}


class PGoApi:

    API_ENTRY = 'https://pgorelease.nianticlabs.com/plfe/rpc'

    def __init__(self, config, pokemon_names, start_pos):

        self.log = logging.getLogger(__name__)
        self._start_pos = start_pos
        self._walk_count = 1
        self._auth_provider = None
        self._api_endpoint = None
        self.config = config
        self.set_position(*start_pos)
        self._pokeball_type = 1
        self.MIN_KEEP_IV = config.get("MIN_KEEP_IV", 0)
        self.KEEP_CP_OVER = config.get("KEEP_CP_OVER", 0)
        self.RELEASE_DUPLICATES = config.get("RELEASE_DUPLICATE", 0)
        self.DUPLICATE_CP_FORGIVENESS = config.get("DUPLICATE_CP_FORGIVENESS", 0)
        self.MAX_BALL_TYPE = config.get("MAX_BALL_TYPE", 0)
        self._req_method_list = []
        self._heartbeat_number = 5
        self.pokemon_names = pokemon_names
        self.pokeballs = [0, 0, 0, 0]  # pokeball counts. set to 0 to force atleast one fort check  before trying to capture pokemon
        self.min_item_counts = dict(
            ((getattr(Inventory, key), value) for key, value in config.get('MIN_ITEM_COUNTS', {}).iteritems())
        )

    def call(self):
        if not self._req_method_list:
            return False

        if self._auth_provider is None or not self._auth_provider.is_login():
            self.log.info('Not logged in')
            return False

        player_position = self.get_position()

        request = RpcApi(self._auth_provider)

        if self._api_endpoint:
            api_endpoint = self._api_endpoint
        else:
            api_endpoint = self.API_ENTRY

        self.log.debug('Execution of RPC')
        response = None
        try:
            response = request.request(api_endpoint, self._req_method_list, player_position)
        except ServerBusyOrOfflineException:
            self.log.info('Server seems to be busy or offline - try again!')

        # cleanup after call execution
        self.log.debug('Cleanup of request!')
        self._req_method_list = []

        return response

    def list_curr_methods(self):
        for i in self._req_method_list:
            print("{} ({})".format(RequestType.Name(i), i))

    def set_logger(self, logger):
        self._ = logger or logging.getLogger(__name__)

    def get_position(self):
        return (self._position_lat, self._position_lng, self._position_alt)

    def set_position(self, lat, lng, alt):
        self.log.debug('Set Position - Lat: %s Long: %s Alt: %s', lat, lng, alt)
        self._posf = (lat, lng, alt)
        self._position_lat = f2i(lat)
        self._position_lng = f2i(lng)
        self._position_alt = f2i(alt)

    def __getattr__(self, func):
        def function(**kwargs):

            if not self._req_method_list:
                self.log.debug('Create new request...')

            name = func.upper()
            if kwargs:
                self._req_method_list.append({RequestType.Value(name): kwargs})
                self.log.debug("Adding '%s' to RPC request including arguments", name)
                self.log.debug("Arguments of '%s': \n\r%s", name, kwargs)
            else:
                self._req_method_list.append(RequestType.Value(name))
                self.log.debug("Adding '%s' to RPC request", name)

            return self

        if func.upper() in RequestType.keys():
            return function
        else:
            raise AttributeError

    def heartbeat(self):
        self.get_player()
        if self._heartbeat_number % 10 == 0:  # every 10 heartbeats do a inventory check
            self.check_awarded_badges()
            self.get_inventory()
        res = self.call()
        if res.get("direction", -1) == 102:
            self.log.error("There were a problem responses for api call: %s. Restarting!!!", res)
            raise AuthException("Token probably expired?")
        self.log.debug('Heartbeat dictionary: \n\r{}'.format(json.dumps(res, indent=2)))

        if 'GET_PLAYER' in res['responses']:
            player_data = res['responses'].get('GET_PLAYER', {}).get('player_data', {})
            if os.path.isfile("accounts/%s.json" % self.config['username']):
                with open("accounts/%s.json" % self.config['username'], "r") as f:
                    file = f.read()
                    json_file = json.loads(file)
                inventory_items = json_file.get('GET_INVENTORY', {}).get('inventory_delta', {}).get('inventory_items', [])
                inventory_items_dict_list = map(lambda x: x.get('inventory_item_data', {}), inventory_items)
                player_stats = filter(lambda x: 'player_stats' in x, inventory_items_dict_list)[0].get('player_stats', {})
            else:
                player_stats = {}
            currencies = player_data.get('currencies', [])
            currency_data = ",".join(map(lambda x: "{0}: {1}".format(x.get('name', 'NA'), x.get('amount', 'NA')), currencies))
            self.log.info("Username: %s, Lvl: %s, XP: %s/%s, Currencies: %s", player_data.get('username', 'NA'), player_stats.get('level', 'NA'), player_stats.get('experience', 'NA'), player_stats.get('next_level_xp', 'NA'), currency_data)  # display stats

        if 'GET_INVENTORY' in res['responses']:
            with open("accounts/%s.json" % self.config['username'], "w") as f:
                res['responses']['lat'] = self._posf[0]
                res['responses']['lng'] = self._posf[1]
                f.write(json.dumps(res['responses'], indent=2))
            self.log.info("List of Pokemon:\n" + get_inventory_data(res, self.pokemon_names) + "\nTotal Pokemon count: " + str(get_pokemon_num(res)) + "\nEgg Hatching status: " + get_incubators_stat(res))
            self.log.debug(self.cleanup_inventory(res['responses']['GET_INVENTORY']['inventory_delta']['inventory_items']))

        self._heartbeat_number += 1
        return res

    def walk_to(self, loc):
        self._walk_count += 1
        steps = get_route(self._posf, loc, self.config.get("USE_GOOGLE", False), self.config.get("GMAPS_API_KEY", ""))
        for step in steps:
            for i, next_point in enumerate(get_increments(self._posf, step, self.config.get("STEP_SIZE", 200))):
                self.set_position(*next_point)
                self.heartbeat()
                self.log.info("Sleeping before next heartbeat")
                sleep(2)  # If you want to make it faster, delete this line... would not recommend though
                # make sure we have atleast 1 ball
                if sum(self.pokeballs) > 0:
                    while self.catch_near_pokemon():
                        sleep(1) # If you want to make it faster, delete this line... would not recommend though

    # this is in charge of spinning a pokestop
    def spin_near_fort(self):
        map_cells = self.nearby_map_objects().get('responses', {}).get('GET_MAP_OBJECTS', {}).get('map_cells', {})
        forts = PGoApi.flatmap(lambda c: c.get('forts', []), map_cells)
        if self._start_pos and self._walk_count % self.config.get("RETURN_START_INTERVAL") == 0:
            destinations = filtered_forts(self._start_pos, forts)
        else:
            destinations = filtered_forts(self._posf, forts)

        if destinations:
            destination_num = random.randint(0, min(5, len(destinations) - 1))
            fort = destinations[destination_num]
            self.log.info("Walking to fort at %s,%s", fort['latitude'], fort['longitude'])
            self.walk_to((fort['latitude'], fort['longitude']))
            position = self._posf # FIXME ?
            res = self.fort_search(fort_id=fort['id'], fort_latitude=fort['latitude'], fort_longitude=fort['longitude'], player_latitude=position[0], player_longitude=position[1]).call()['responses']['FORT_SEARCH']
            self.log.debug("Fort spinned: %s", res)
            if 'lure_info' in fort:
                encounter_id = fort['lure_info']['encounter_id']
                fort_id = fort['lure_info']['fort_id']
                position = self._posf
                resp = self.disk_encounter(encounter_id=encounter_id, fort_id=fort_id, player_latitude=position[0], player_longitude=position[1]).call()['responses']['DISK_ENCOUNTER']
                self.log.debug('Encounter response is: %s', resp)
                if self.pokeballs[1] > 9 and self.pokeballs[2] > 4 and self.pokeballs[3] > 4:
                    self.disk_encounter_pokemon(fort['lure_info'])
            return True
        else:
            self.log.error("No fort to walk to!")
            return False

    # this will catch any nearby pokemon
    def catch_near_pokemon(self):
        map_cells = self.nearby_map_objects().get('responses', {}).get('GET_MAP_OBJECTS', {}).get('map_cells', {})
        pokemons = PGoApi.flatmap(lambda c: c.get('catchable_pokemons', []), map_cells)

        # catch first pokemon:
        origin = (self._posf[0], self._posf[1])
        pokemon_distances = [(pokemon, distance_in_meters(origin, (pokemon['latitude'], pokemon['longitude']))) for pokemon in pokemons]
        self.log.debug("Nearby pokemon: : %s", pokemon_distances)
        for pokemon_distance in pokemon_distances:
            target = pokemon_distance
            self.log.debug("Catching pokemon: : %s, distance: %f meters", target[0], target[1])
            self.log.info("Catching Pokemon: %s", self.pokemon_names[str(target[0]['pokemon_id'])])
            return self.encounter_pokemon(target[0])
            if sum(self.pokeballs) == 0:
                self.spin_near_fort()
        return False

    def nearby_map_objects(self):
        position = self.get_position()
        neighbors = get_neighbors(self._posf)
        return self.get_map_objects(latitude=position[0], longitude=position[1], since_timestamp_ms=[0] * len(neighbors), cell_id=neighbors).call()

    def attempt_catch(self, encounter_id, spawn_point_guid, ball_type):
        r = self.catch_pokemon(
            normalized_reticle_size=1.950,
            pokeball=ball_type,
            spin_modifier=0.850,
            hit_pokemon=True,
            normalized_hit_position=1,
            encounter_id=encounter_id,
            spawn_point_guid=spawn_point_guid,
        ).call()['responses']['CATCH_POKEMON']
        self.log.info("Throwing pokeball type: %s", POKEBALLS[ball_type - 1]) # list the pokeball that was thrown
        if "status" in r:
            self.log.debug("Status: %d", r['status'])
            return r

    def cleanup_inventory(self, inventory_items=None):
        if not inventory_items:
            inventory_items = self.get_inventory().call()['responses']['GET_INVENTORY']['inventory_delta']['inventory_items']

        all_actual_items = [xiq['inventory_item_data']["item"] for xiq in inventory_items if "item" in xiq['inventory_item_data']]
        all_actual_item_str = "List of items:\n"
        all_actual_item_count = 0
        all_actual_items = sorted([x for x in all_actual_items if "count" in x], key=lambda x: x["item_id"])
        for xiq in all_actual_items:
            if 1 <= xiq["item_id"] <= 4: # save counts of pokeballs
                self.pokeballs[xiq["item_id"]] = xiq["count"]
            true_item_name = INVENTORY_DICT[xiq["item_id"]]
            all_actual_item_str += "Item_ID " + str(xiq["item_id"]) + "\titem count " + str(xiq["count"]) + "\t(" + true_item_name + ")\n"
            all_actual_item_count += xiq["count"]
        all_actual_item_str += "Total item count: " + str(all_actual_item_count)
        self.log.info(all_actual_item_str)

        caught_pokemon = defaultdict(list)
        for inventory_item in inventory_items:
            if "pokemon_data" in inventory_item['inventory_item_data']:
                # is a pokemon:
                pokemon = inventory_item['inventory_item_data']['pokemon_data']
                if 'cp' in pokemon and "favorite" not in pokemon:
                    caught_pokemon[pokemon["pokemon_id"]].append(pokemon)
            elif "item" in inventory_item['inventory_item_data']:
                item = inventory_item['inventory_item_data']['item']
                if item['item_id'] in self.min_item_counts and "count" in item and item['count'] > self.min_item_counts[item['item_id']]:
                    recycle_count = item['count'] - self.min_item_counts[item['item_id']]
                    self.log.info("Recycling {0}, item count {1}".format(INVENTORY_DICT[item['item_id']], recycle_count))
                    self.recycle_inventory_item(item_id=item['item_id'], count=recycle_count)

        for pokemons in caught_pokemon.values():
            if len(pokemons) > MIN_SIMILAR_POKEMON:  # if you have more then same amount of pokemon do this
                pokemons = sorted(pokemons, lambda x, y: cmp(x['cp'], y['cp']), reverse=True)
                for pokemon in pokemons[MIN_SIMILAR_POKEMON:]:
                    if 'cp' in pokemon and pokemon_iv_percentage(pokemon) > self.MIN_KEEP_IV and pokemon["cp"] > self.KEEP_CP_OVER:  # Keep only if the pokemon is over the IV and CP set up
                        if pokemon['pokemon_id'] in CANDY_NEEDED_TO_EVOLVE:
                            for inventory_item in inventory_items:
                                if "pokemon_family" in inventory_item['inventory_item_data'] and inventory_item['inventory_item_data']['pokemon_family']['family_id'] == pokemon['pokemon_id'] and inventory_item['inventory_item_data']['pokemon_family']['candy'] > CANDY_NEEDED_TO_EVOLVE[pokemon['pokemon_id']]:
                                    self.log.info("Evolving pokemon: %s", self.pokemon_names[str(pokemon['pokemon_id'])])
                                    self.evolve_pokemon(pokemon_id=pokemon['id'])
                    else:
                        if pokemon['pokemon_id'] in CANDY_NEEDED_TO_EVOLVE:
                            for inventory_item in inventory_items:
                                if "pokemon_family" in inventory_item['inventory_item_data'] and inventory_item['inventory_item_data']['pokemon_family']['family_id'] == pokemon['pokemon_id'] and inventory_item['inventory_item_data']['pokemon_family']['candy'] > CANDY_NEEDED_TO_EVOLVE[pokemon['pokemon_id']]:
                                    self.log.info("Evolving pokemon: %s", self.pokemon_names[str(pokemon['pokemon_id'])])
                                    self.evolve_pokemon(pokemon_id=pokemon['id'])
                        self.log.debug("Releasing pokemon: %s", pokemon)
                        self.log.info("Releasing pokemon: %s IV: %s", self.pokemon_names[str(pokemon['pokemon_id'])], pokemon_iv_percentage(pokemon))
                        self.release_pokemon(pokemon_id=pokemon["id"])

        if self.RELEASE_DUPLICATES:
            for pokemons in caught_pokemon.values():
                if len(pokemons) > MIN_SIMILAR_POKEMON:
                    pokemons = sorted(pokemons, lambda x, y: cmp(self.pokemon_names[str(x['pokemon_id'])], self.pokemon_names[str(y['pokemon_id'])]))
                    last_pokemon = pokemons[0]
                    for pokemon in pokemons[MIN_SIMILAR_POKEMON:]:
                        if self.pokemon_names[str(pokemon['pokemon_id'])] == self.pokemon_names[str(last_pokemon['pokemon_id'])]:
                            # Compare two pokemon if the larger IV pokemon has less then DUPLICATE_CP_FORGIVENESS times CP keep it
                            if pokemon_iv_percentage(pokemon) > pokemon_iv_percentage(last_pokemon):
                                if pokemon['cp'] * self.DUPLICATE_CP_FORGIVENESS < last_pokemon['cp']:
                                    # release the lesser!
                                    self.log.debug("Releasing pokemon: %s", last_pokemon)
                                    self.log.info("Releasing pokemon: %s IV: %s", self.pokemon_names[str(last_pokemon['pokemon_id'])], pokemon_iv_percentage(last_pokemon))
                                    self.release_pokemon(pokemon_id=last_pokemon["id"])
                                last_pokemon = pokemon
                            else:
                                if last_pokemon['cp'] * self.DUPLICATE_CP_FORGIVENESS > pokemon['cp']:
                                    # release the lesser!
                                    self.log.debug("Releasing pokemon: %s", pokemon)
                                    self.log.info("Releasing pokemon: %s IV: %s", self.pokemon_names[str(pokemon['pokemon_id'])], pokemon_iv_percentage(pokemon))
                                    self.release_pokemon(pokemon_id=pokemon["id"])

                        else:
                            last_pokemon = pokemon

        return self.call()

    def disk_encounter_pokemon(self, lureinfo):
        try:
            encounter_id = lureinfo['encounter_id']
            fort_id = lureinfo['fort_id']
            position = self._posf
            resp = self.disk_encounter(encounter_id=encounter_id, fort_id=fort_id, player_latitude=position[0], player_longitude=position[1]).call()['responses']['DISK_ENCOUNTER']
            if resp['result'] == 1:
                capture_status = -1
                self._pokeball_type = 1
                while capture_status != 0 and capture_status != 3:
                    for balls in range(len(self.pokeballs)):
                        self._pokeball_type = balls
                        if self.pokeballs[balls] > 0:
                            catch_attempt = self.attempt_catch(encounter_id, fort_id, self._pokeball_type)
                            self.pokeballs[self._pokeball_type] -= 1
                            capture_status = catch_attempt['status']
                            if capture_status == 1:
                                self.log.debug("Caught Pokemon: : %s", catch_attempt)
                                self.log.info("Caught Pokemon:  %s", self.pokemon_names[str(resp['pokemon_data']['pokemon_id'])])
                                self._pokeball_type = 1
                                sleep(2) # If you want to make it faster, delete this line... would not recommend though
                                return catch_attempt
                            elif capture_status == 2:
                                self.log.info("Pokemon %s is too wild", self.pokemon_names[str(resp['pokemon_data']['pokemon_id'])])
                                if self._pokeball_type < self.MAX_BALL_TYPE:
                                    self._pokeball_type += 1
                            elif capture_status == 3:
                                self.log.debug("Failed Catch: : %s", catch_attempt)
                                self.log.info("Failed to Catch Pokemon:  %s", self.pokemon_names[str(resp['pokemon_data']['pokemon_id'])])
                                self._pokeball_type = 1
                    sleep(2) # If you want to make it faster, delete this line... would not recommend though
            return False
        except Exception as e:
            self.log.error("Error in disk encounter %s", e)
            self._pokeball_type = 1
            return False

    def encounter_pokemon(self, pokemon):
        encounter_id = pokemon['encounter_id']
        spawn_point_id = pokemon['spawn_point_id']
        position = self._posf
        encounter = self.encounter(
            encounter_id=encounter_id,
            spawn_point_id=spawn_point_id,
            player_latitude=position[0],
            player_longitude=position[1]
        ).call()['responses']['ENCOUNTER']
        # this cade catches pokemon
        self.log.debug("Started Encounter: %s", encounter)
        if encounter['status'] == 1:
            capture_status = -1
            self._pokeball_type = 1  # start with a pokeball
            while capture_status != 0 and capture_status != 3:
                for balls in range(len(self.pokeballs)):  # try with each ball type starting with weakest
                    self._pokeball_type = balls
                    if self.pokeballs[balls] > 0:  # if you have less then 1 ball do not attempt to catch em all
                        catch_attempt = self.attempt_catch(encounter_id, spawn_point_id, self._pokeball_type)  # actual catching code
                        self.pokeballs[self._pokeball_type] -= 1  # lowers the thrown ball code
                        capture_status = catch_attempt['status']
                        if capture_status == 1:
                            self.log.debug("Caught Pokemon: : %s", catch_attempt)  # you did it
                            self.log.info("Caught Pokemon:  %s", self.pokemon_names[str(pokemon['pokemon_id'])])
                            self._pokeball_type = 1
                            sleep(2) # If you want to make it faster, delete this line... would not recommend though
                            return catch_attempt
                        elif capture_status == 2:
                            self.log.info("Pokemon %s is too wild", self.pokemon_names[str(pokemon['pokemon_id'])])
                            if self._pokeball_type < self.MAX_BALL_TYPE:
                                self._pokeball_type += 1  # try with a stronger ball
                        elif capture_status == 3:
                            self.log.debug("Failed Catch: : %s", catch_attempt)  # potential soft ban or just a run away
                            self.log.info("Failed to Catch Pokemon:  %s", self.pokemon_names[str(pokemon['pokemon_id'])])
                            self._pokeball_type = 1
                sleep(2) # If you want to make it faster, delete this line... would not recommend though
        return False

    def login(self, provider, username, password, cached=False):
        if not isinstance(username, basestring) or not isinstance(password, basestring):
            raise AuthException("Username/password not correctly specified")

        if provider == 'ptc':
            self._auth_provider = AuthPtc()
        elif provider == 'google':
            self._auth_provider = AuthGoogle()
        else:
            raise AuthException("Invalid authentication provider - only ptc/google available.")

        self.log.debug('Auth provider: %s', provider)

        if not self._auth_provider.login(username, password):
            self.log.info('Login process failed')
            return False

        self.log.info('Starting RPC login sequence (app simulation)')
        self.get_player()
        self.get_hatched_eggs()
        self.get_inventory()
        self.check_awarded_badges()
        self.download_settings(hash="05daf51635c82611d1aac95c0b051d3ec088a930")  # not sure what this is but dont change it

        response = self.call()

        if not response:
            self.log.info('Login failed!')
        if os.path.isfile("auth_cache") and cached:
            response = pickle.load(open("auth_cache"))
        fname = "auth_cache_%s" % username
        if os.path.isfile(fname) and cached:
            response = pickle.load(open(fname))
        else:
            response = self.heartbeat()
            f = open(fname, "w")
            pickle.dump(response, f)
        if not response:
            self.log.info('Login failed!')
            return False

        if 'api_url' in response:
            self._api_endpoint = ('https://{}/rpc'.format(response['api_url']))
            self.log.debug('Setting API endpoint to: %s', self._api_endpoint)
        else:
            self.log.error('Login failed - unexpected server response!')
            return False

        if 'auth_ticket' in response:
            self._auth_provider.set_ticket(response['auth_ticket'].values())

        self.log.info('Finished RPC login sequence (app simulation)')
        self.log.info('Login process completed')

        return True

    def main_loop(self):
        self.heartbeat()
        while True:
            self.heartbeat()
            sleep(1) # If you want to make it faster, delete this line... would not recommend though
            if sum(self.pokeballs) > 0:  # if you do not have any balls skip pokemon catching
                while self.catch_near_pokemon():
                    sleep(4) # If you want to make it faster, delete this line... would not recommend though
            else:
                self.log.info("Less than 1 Poke Balls: Entering pokestops only")
            self.spin_near_fort()  # check local pokestop

    @staticmethod
    def flatmap(f, items):
        return chain.from_iterable(imap(f, items))
