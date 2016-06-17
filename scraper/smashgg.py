import os
import requests
from model import MatchResult
from garprLogging.log import Log

BASE_SMASHGG_API_URL = "https://api.smash.gg/phase_group/"
TOURNAMENT_URL = os.path.join(BASE_SMASHGG_API_URL, '%s')
DUMP_SETTINGS = "?expand[0]=sets&expand[1]=seeds&expand[2]=entrants&expand[3]=matches"

class SmashGGScraper(object):
    def __init__(self, tournament_id):
        """
        :param tournament_id:
        """
        self.tournament_id = tournament_id
        self.raw_dict = None
        self.players = []

        try:
            self.get_raw()
        except Exception as ex:
            return ex.message


    def get_raw(self):
        """
        :return: the JSON dump that the api call returns
        """
        try:
            if self.raw_dict == None:
                self.raw_dict = {}

                base_url = TOURNAMENT_URL % self.tournament_id
                url = base_url + DUMP_SETTINGS

                self.log('API Call to ' + str(url) + ' executing')
                self.raw_dict['smashgg'] = self._check_for_200(requests.get(url)).json()
            return self.raw_dict
        except Exception as ex:
            msg = 'An error occurred in the retrieval of data from SmashGG: ' + str(ex)
            Log.log('SmashGG', msg)
            return msg

    def get_matches(self):
        """
        :return: the list of MatchResult objects that represents every match
        played in the given bracket, including who won and who lost
        """
        matches = []
        try:
            sets = self.get_raw()['smashgg']['entities']['sets']
            for set in sets:
                winner_id = set['winnerId']
                loser_id = set['loserId']
                # CHECK FOR A BYE
                if loser_id is None:
                    continue

                winner = self.get_player_by_entrant_id(winner_id)
                loser = self.get_player_by_entrant_id(loser_id)

                match = MatchResult(winner.smash_tag, loser.smash_tag)
                matches.append(match)
        except Exception as ex:
            msg = 'An error occurred in the retrieval of matches from SmashGG: ' + str(ex)
            Log.log('SmashGG', msg)
        return matches

    def get_player_by_entrant_id(self, id):
        """
        :param id: id of the entrant for the current tournament
        :return: a SmashGGPlayer object that belongs to the given tournament entrant number
        """
        player = None
        try:
            if self.players is None or len(self.players) == 0:
                self.get_smashgg_players()

            for player in self.players:
                if id == int(player.entrant_id):
                    return player
        except Exception as ex:
            msg = 'An error occurred in the retrieval of SmashGG Entrant ' + id + ': ' + str(ex.message)
            Log.log('SmashGG', msg)
        return player

    def get_player_by_smashgg_id(self, id):
        """
        :param id: id of the smashGG  player's account
        :return: a SmashGGPlayer object that belongs to the given smashgg id number
        """
        player = None
        try:
            if self.players is None or len(self.players) == 0:
                self.get_smashgg_players()

            for player in self.players:
                if id == int(player.smashgg_id):
                    return player
        except Exception as ex:
            msg = 'An error occurred in the retrieval of SmashGG Player ' + id + ': ' + str(ex.message)
            Log.log('SmashGG', msg)
        return player

    def get_players(self):
        """
        :return: the smash tags of every player who is in the given bracket
        """
        tags = []
        try:
            if self.players is None or len(self.players) == 0:
                self.get_smashgg_players()

            for player in self.players:
                tags.append(str(player.smash_tag).strip())
        except Exception as ex:
            msg = 'An error occurred in the retrieval of players from SmashGG: ' + str(ex.message)
            Log.log('SmashGG', msg)
        return tags

    def get_smashgg_players(self):
        """
        :return: and edit the local list of SmashGGPlayer objects that encapsulate important information about
        the participants of the tournament, including their name, region, smashtag,
        tournament entrant id, and overall smashgg id
        """
        self.players = []
        try:
            seeds = self.get_raw()['smashgg']['entities']['seeds']
            for seed in seeds:
                tag = None
                name = None
                state = None
                country = None
                region = None

                #ACCESS THE PLAYERS IN THE JSON AND EXTRACT THE SMASHTAG
                #IF NO SMASHTAG, WE SHOULD SKIP TO THE NEXT ITERATION
                entrant_id = seed['entrantId']
                this_player = seed['mutations']['players']
                for player_id in this_player:
                    id = player_id

                try:
                    tag = this_player[id]['gamerTag'].strip()
                except:
                    print self.log('Player for id ' + str(id) + ' not found')
                    continue

                #EXTRACT EXTRA DATA FROM SMASHGG WE MAY WANT TO USE LATER
                #ENCAPSULATE IN A SMASHGG SPECIFIC MODEL
                try:
                    name = this_player[id]['name'].strip()
                except Exception as e:
                    name = None
                    print self.log('SmashGGPlayer ' + tag + ': name | ' + str(e))

                try:
                    region = this_player[id]['region'].strip()
                except Exception as regionEx:
                    print self.log('SmashGGPlayer ' + tag + ': region | ' + str(regionEx))

                try:
                    state = this_player[id]['state'].strip()
                    if region is None:
                        region = state
                except Exception as stateEx:
                    print self.log('SmashGGPlayer ' + tag + ': state | ' + str(stateEx))

                try:
                    country = this_player[id]['country'].strip()
                    if region is None:
                        region = country
                except Exception as countryEx:
                    print self.log('SmashGGPlayer ' + tag + ': country | ' + str(countryEx))



                player = SmashGGPlayer(smashgg_id=id, entrant_id=entrant_id, name=name, smash_tag=tag, region=region,
                                       state=state, country=country)
                self.players.append(player)
        except Exception as ex:
            msg = 'An error occurred in the retrieval of SmashGG Players: ' + str(ex.message)
            Log.log('SmashGG', msg)
        return self.players

    def get_smashgg_matches(self):
        """
        :return: a list of SmashGGMatch objects that encapsulate more data about the match
        than just the winner and loser. Could be useful for additional ranking metrics
        like how far into the tournament or how many matches were played.
        """
        self.matches = []
        try:
            sets = self.get_raw()['smashgg']['entities']['sets']
            for set in sets:
                winner_id = set['winnerId']
                loser_id = set['loserId']
                # CHECK FOR A BYE
                if loser_id is None:
                    continue

                try:
                    name = set['fullRoundText']
                    round = set['round']
                    bestOf = set['bestOf']
                except:
                    print self.log('Could not find extra details for match')
                    round = None
                    bestOf = None

                match = SmashGGMatch(name, winner_id, loser_id, round, bestOf)
                self.matches.append(match)
        except Exception as ex:
            msg = 'An error occurred in the retrieval of SmashGG Matches: ' + str(ex.message)
            Log.log('SmashGG', msg)
        return self.matches

    def _check_for_200(self, response):
        """
        :param response: http response to check for correct http code
        :return: the body response from a successful http call
        """
        try:
            response.raise_for_status()
        except Exception as ex:
            msg = 'An error occurred in the http request to SmashGG: ' + str(ex.message)
            Log.log('SmashGG', msg)
        return response

    def log(self, msg):
        """
        :param msg: error or log message to print or write
        :return: a string that can be used for logging
        """
        return "    [SmashGG] " + msg

    @staticmethod
    def get_tournament_id_from_url(url):
        """
        Parses a url and retrieves the unique id of the bracket in question
        :param url: url to parse the tournament id from
        :return: the unique id of the bracket in question
        """
        try:
            id = url[url.rfind('/') + 1:]
        except Exception as ex:
            msg = 'An error occurred in parsing out the SmashGG tournament id: ' + str(ex.message)
            Log.log('SmashGG', msg)
        return int(id)

    @staticmethod
    def get_tournament_name_from_url(url):
        """
        Parses a url and retrieves the name of the tournament in question
        :param url: url to parse the tournament name from
        :return: the name of the tournament in question
        """
        name = None
        try:
            tStr = 'tournament/'
            startIndex = url.rfind(tStr) + len(tStr)
            name = url[startIndex: url.index('/', startIndex)]
            name = name.replace('-', ' ')
        except Exception as ex:
            msg = 'An error occurred in parsing out the SmashGG tournament name: ' + str(ex.message)
            Log.log('SmashGG', msg)
        return name

class SmashGGPlayer(object):
    def __init__(self, smashgg_id, entrant_id, name, smash_tag, region, country, state):
        """
        :param smashgg_id: The Global id that a player is mapped to on the website
        :param entrant_id: The id assigned to an entrant for the given tournament
        :param name:       The real name of the player
        :param smash_tag:  The Smash Tag of the player
        :param region:     The region the player belongs to
        """
        self.smashgg_id = smashgg_id
        self.entrant_id = entrant_id
        self.name = name
        self.smash_tag = smash_tag
        self.region = region
        self.country = country
        self.state = state

class SmashGGMatch(object):
    def __init__(self, roundName, winner_id, loser_id, roundNumber, bestOf):
        """
        :param winner_id: Entrant id of the winner of the match
        :param loser_id:  Entrant id of the loser of the match
        :param round:     Round of the bracket this match took place
        :param bestOf:    Best of this many matches
        """
        self.roundName = roundName
        self.winner_id = winner_id
        self.loser_id = loser_id
        self.roundNumber = roundNumber
        self.bestOf = bestOf

class SmashGGException(Exception):
    def __init__(self, message):
        self.message = message