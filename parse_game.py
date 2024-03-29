import os
import re
import json
import logging
import pandas as pd
import numpy as np

from datetime import datetime


class ParseGame(object):
    """ This class contains the code necessary to parse a game and write it to a database

	Attributes:
		filepath: A string indicating the path to the file
		dbcon: An object containing the database connection
		logger: A logger to keep track of events
	"""

    def __init__(self, filepath="", logpath="gameparser.log"):
        """ Inits empty class
		"""
        self.filepath = ""
        self.logpath = logpath
        logging.basicConfig(
            filename=logpath,
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%H:%M:%S",
        )
        self.logger = logging.getLogger("ParseGame")

    def attach_filepath(self, filepath):
        """ Method to attach and validate filepath
        TODO: check that filepath is valid
        """
        if (
            os.path.exists(filepath)
            and os.path.isfile(filepath)
            and filepath[-4:] == "json"
        ):
            self.filepath = filepath
            self.logger.info("Attached filepath " + filepath)
        else:
            raise ValueError(
                "Path either doesn't exist, is not a file, or is not a JSON"
            )

    def import_game(self):
        """ Reads in the game JSON file, get basic game info such as match id, league and season
		"""
        self.logger.info("Reading in file " + self.filepath)
        with open(self.filepath) as f:
            self.data = json.load(f)
        self.logger.info("Finished reading in file " + self.filepath)

        self.logger.info("Gathering match id, league, season")
        self.match_id = int(re.findall("\d{6}", self.filepath)[0])
        self.league = re.findall("[A-Z]{3}\d", self.filepath)[0]
        self.season = re.findall("\d{4}-\d{4}", self.filepath)[
            0
        ]  # TODO: Fix this for single year seasons
        self.logger.info("Retrieved match id, league, season")
        self.logger.info(
            "Working on match "
            + str(self.match_id)
            + " in league "
            + self.league
            + " in season "
            + str(self.season)
        )

    def check_game_data(self):
        """ Sanitizes game data to see if there are any glaring errors
		"""
        raise NotImplementedError

    def extract_players(self):
        """ Extract player information, which is only the PlayerId and the name

		TODO: Maybe just roll this into a huge extract_players feature
		"""
        players = self.data["playerIdNameDictionary"]
        player_df = pd.Series(players).explode().reset_index()
        player_df.columns = ["PlayerId", "PlayerName"]
        self.player_data = player_df
        raise NotImplementedError

    def extract_referee(self):
        """ Extract referee data, which is only referee id, name and match id
		"""
        self.logger.info("Retrieving referee data " + str(self.match_id))
        referee_id = int(self.data["referee"]["officialId"])
        referee_name = self.data["referee"]["name"]
        referee_df = pd.DataFrame([self.match_id, referee_id, referee_name]).transpose()
        referee_df.columns = ["MatchId", "RefereeId", "RefereeName"]
        self.referee_data = referee_df
        self.logger.info("Retrieved referee data " + str(self.match_id))

    def extract_player_game(self):
        """ Extract info on player-games
		"""

        def side_player_info(player_list):
            """ Helper function for extract_player_game
            """
            players_df = pd.DataFrame()
            for player in player_list:
                player_id = int(player["playerId"])
                shirt_num = int(player["shirtNo"])
                name = player["name"]
                player_pos = player["position"]
                height = int(player["height"])
                weight = int(player["weight"])
                age = int(player["age"])
                man_of_match = player["isManOfTheMatch"]
                field = player["field"]
                if "subbedOutPlayerId" in player.keys():
                    first_eleven = False
                    subbed_out_player_id = player["subbedOutPlayerId"]
                    subbed_in_minute = player["subbedInExpandedMinute"]
                    subbed_in_half = player["subbedInPeriod"]["displayName"]
                else:
                    first_eleven = True
                    subbed_out_player_id = None
                    subbed_in_minute = None
                    subbed_in_half = None
                player_row = pd.DataFrame(
                    [
                        self.match_id,
                        player_id,
                        shirt_num,
                        name,
                        player_pos,
                        first_eleven,
                        subbed_out_player_id,
                        subbed_in_minute,
                        subbed_in_half,
                        height,
                        weight,
                        age,
                        man_of_match,
                        field,
                    ]
                ).transpose()
                player_row.columns = [
                    "MatchId",
                    "PlayerId",
                    "ShirtNo",
                    "PlayerName",
                    "Position",
                    "Started",
                    "SubOutPlayerId",
                    "SubInMinute",
                    "SubInHalf",
                    "Height",
                    "Weight",
                    "Age",
                    "ManOfMatch",
                    "Field",
                ]
                players_df = players_df.append(player_row)
            return players_df

        self.logger.info("Retrieving player-game info " + str(self.match_id))
        home_players = self.data["home"]["players"]
        away_players = self.data["away"]["players"]
        home_player_df = side_player_info(home_players)
        away_player_df = side_player_info(away_players)
        all_player_df = home_player_df.append(away_player_df)
        all_player_df["MatchId"] = self.match_id
        self.player_game_data = all_player_df
        self.logger.info("Retrieved player-game info for " + str(self.match_id))

    def extract_game(self):
        """ Extract game info
		"""
        self.logger.info("Retrieving game info " + str(self.match_id))
        home_team_id = int(self.data["home"]["teamId"])
        home_team_name = self.data["home"]["name"]
        home_team_manager = self.data["home"]["managerName"]
        home_avg_age = float(self.data["home"]["averageAge"])

        away_team_id = int(self.data["away"]["teamId"])
        away_team_name = self.data["away"]["name"]
        away_team_manager = self.data["away"]["managerName"]
        away_avg_age = float(self.data["away"]["averageAge"])

        home_goals = int(self.data["score"].split(":")[0].strip())
        away_goals = int(self.data["score"].split(":")[1].strip())
        home_ht_goals = int(self.data["htScore"].split(":")[0].strip())
        away_ht_goals = int(self.data["htScore"].split(":")[1].strip())
        home_ft_goals = int(self.data["ftScore"].split(":")[0].strip())
        away_ft_goals = int(self.data["ftScore"].split(":")[1].strip())

        attendance = int(self.data["attendance"])
        venue_name = self.data["venueName"]
        weather_code = self.data["weatherCode"]
        start_time = self.data["startTime"].replace("T", " ")
        start_time = (
            datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
            .time()
            .strftime("%H:%M:%S")
        )
        start_date = self.data["startDate"].replace("T", " ")
        start_date = (
            datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
            .date()
            .strftime("%Y-%m-%d")
        )

        game_info_df = pd.DataFrame(
            [
                self.match_id,
                self.league,
                self.season,
                venue_name,
                attendance,
                start_date,
                start_time,
                weather_code,
                home_team_id,
                home_team_name,
                home_team_manager,
                home_avg_age,
                away_team_id,
                away_team_name,
                away_team_manager,
                away_avg_age,
                home_goals,
                away_goals,
                home_ht_goals,
                away_ht_goals,
                home_ft_goals,
                away_ft_goals,
            ]
        ).transpose()
        game_info_df.columns = [
            "MatchId",
            "League",
            "Season",
            "VenueName",
            "Attendance",
            "StartDate",
            "StartTime",
            "WeatherCode",
            "HomeTeamId",
            "HomeTeamName",
            "HomeTeamManager",
            "HomeAvgAge",
            "AwayTeamId",
            "AwayTeamName",
            "AwayTeamManager",
            "AwayAvgAge",
            "HomeGoals",
            "AwayGoals",
            "HomeHTGoals",
            "AwayHTGoals",
            "HomeFTGoals",
            "AwayFTGoals",
        ]
        # game_info_df["StartTime"] = pd.to_datetime(game_info_df["StartTime"])
        # game_info_df["StartDate"] = pd.to_datetime(game_info_df["StartDate"])
        self.game_data = game_info_df
        self.logger.info("Retrieved game info " + str(self.match_id))

    def extract_events(self):
        """ Extracts event info
        """
        self.logger.info("Retrieving events  " + str(self.match_id))
        event_df = pd.DataFrame()
        for event in self.data["events"]:
            try:
                event_id = int(event["id"])
            except:
                event_id = None
            try:
                event_match_id = int(event["eventId"])
            except:
                event_match_id = None
            minute = int(event["minute"])
            try:
                second = int(event["second"])
            except:
                second = None
            event_team_id = int(event["teamId"])
            if "playerId" in event.keys():
                player_id = int(event["playerId"])
            else:
                player_id = None
            start_x = float(event["x"])
            end_y = float(event["y"])
            period = event["period"]["displayName"]
            event_type = event["type"]["displayName"]
            outcome = event["outcomeType"]["displayName"]
            if "endX" in event.keys():
                end_x = float(event["endX"])
                end_y = float(event["endY"])
            else:
                end_x = None
                end_y = None
            # quals = event['qualifiers']
            # for q in quals:
            #     if q['type']['displayName'] == "Zone":
            #         zone = q['value']
            #     else:
            #         zone = None
            #     if q['type']['displayName'] == "Angle":
            #         angle = q['value']
            #     else:
            #         angle = None
            #     if q['type']['displayName'] == "Angle":
            #         angle = q['value']
            #     else:
            #         angle = None
            event_row = pd.DataFrame(
                [
                    self.match_id,
                    event_id,
                    event_match_id,
                    minute,
                    second,
                    event_team_id,
                    player_id,
                    start_x,
                    end_y,
                    period,
                    event_type,
                    outcome,
                    end_x,
                    end_y,
                ]
            ).transpose()
            event_row.columns = [
                "MatchId",
                "EventId",
                "EventMatchId",
                "Minute",
                "Second",
                "TeamId",
                "PlayerId",
                "StartX",
                "StartY",
                "Half",
                "Type",
                "Outcome",
                "EndX",
                "EndY",
            ]
            event_df = event_df.append(event_row)
        self.event_data = event_df
        self.logger.info("Retrieved events for " + str(self.match_id))
