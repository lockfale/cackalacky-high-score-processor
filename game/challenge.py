import logging
import os
from typing import Dict

import pandas
import redis

from connectors.pgsql import PostgreSQLConnector
from game.sql_helper import open_sql_file

logger = logging.getLogger("s3logger")


# current working directory is going to be the root of the project
SCORE_BY_SCORE_ID_QRY = open_sql_file("game/queries/get_score_by_score_id.sql")
CHALLENGE_BY_USER_UUID_MAC_AND_GAME_NAME = open_sql_file("game/queries/get_challenge_by_user_uuid_mac_and_game_name.sql")
CHALLENGE_BY_CHALLENGE_ID = open_sql_file("game/queries/get_challenge_by_challenge_id.sql")
UPDATE_CHALLENGER_SCORE = open_sql_file("game/queries/update_challenger_score.sql")
UPDATE_CHALLENGEE_SCORE = open_sql_file("game/queries/update_challengee_score.sql")
UPDATE_CHALLENGE_WINNER = open_sql_file("game/queries/update_challenge_winner.sql")


def update_challenge_row_submitted_score(db: PostgreSQLConnector, user_uuid: str, mac_address: str, score_id: int, game_name: str) -> Dict[str, int]:
    """

    Parameters
    ----------
    db: PostgreSQLConnector
    user_uuid: str
    mac_address: str
    score_id: str
    game_name: str

    Returns
    -------
    Dict[str, int]
    """
    logger.info(f"Retrieving the role of the user who scored by uuid: {user_uuid}")
    who_is = db.select_dataframe(
        query=CHALLENGE_BY_USER_UUID_MAC_AND_GAME_NAME,
        args={
            "game": game_name,
            "uuid": user_uuid,
            "mac_address": mac_address,
        },
    )
    logger.info(who_is)
    who_is = who_is.to_dict("records")

    challenger_row_id = who_is[0].get("challenger_row_id_challenger")
    challengee_row_id = who_is[0].get("challenger_row_id_challengee")

    if challenger_row_id:
        logger.info("Found existing, valid challenge with the user as the challenger...")
        params = {"score_id": score_id, "id": challenger_row_id}
        _ = db.execute(query=UPDATE_CHALLENGER_SCORE, args=params)

    if challengee_row_id:
        logger.info("Found existing, valid challenge with the user as the challengee...")
        params = {"score_id": score_id, "id": challengee_row_id}
        _ = db.execute(query=UPDATE_CHALLENGEE_SCORE, args=params)

    return {
        "challenger_row_id": challenger_row_id,
        "challengee_row_id": challengee_row_id,
    }


def set_participant_details(participant_dict, discord_id, score, duration):
    """

    Parameters
    ----------
    participant_dict: dict
    discord_id: str
    score: str
    duration: str

    Returns
    -------
    dict
    """
    participant_dict["discord_user_id"] = discord_id
    participant_dict["score"] = score
    participant_dict["duration"] = duration


def set_outcome_dictionary(challenge_row: dict, challenger_score_row: dict, challengee_score_row: dict) -> Dict[str, Dict]:
    """

    Parameters
    ----------
    challenge_row: dict
    challenger_score_row: dict
    challengee_score_row: dict

    Returns
    -------
    Dict[str, Dict]
    """
    winner, loser = {}, {}

    if challenger_score_row["score"] > challengee_score_row["score"]:
        set_participant_details(winner, challenge_row["challenger_discord_id"], challenger_score_row["score"], challenger_score_row["duration"])
        set_participant_details(loser, challenge_row["challengee_discord_id"], challengee_score_row["score"], challengee_score_row["duration"])
    elif challenger_score_row["score"] < challengee_score_row["score"]:
        set_participant_details(loser, challenge_row["challenger_discord_id"], challenger_score_row["score"], challenger_score_row["duration"])
        set_participant_details(winner, challenge_row["challengee_discord_id"], challengee_score_row["score"], challengee_score_row["duration"])
    else:
        if challenger_score_row["duration"] < challengee_score_row["duration"]:
            set_participant_details(winner, challenge_row["challenger_discord_id"], challenger_score_row["score"], challenger_score_row["duration"])
            set_participant_details(loser, challenge_row["challengee_discord_id"], challengee_score_row["score"], challengee_score_row["duration"])
        elif challenger_score_row["duration"] > challengee_score_row["duration"]:
            set_participant_details(loser, challenge_row["challenger_discord_id"], challenger_score_row["score"], challenger_score_row["duration"])
            set_participant_details(winner, challenge_row["challengee_discord_id"], challengee_score_row["score"], challengee_score_row["duration"])

    return {"winner": winner, "loser": loser}


def process_winner_loser(db: PostgreSQLConnector, winner: Dict, loser: Dict, challenge_row: Dict):
    """

    Parameters
    ----------
    db: PostgreSQLConnector
    winner: Dict
    loser: Dict
    challenge_row: Dict
    """
    string_me = (
        f"<@{winner['discord_user_id']}> won the challenge against <@{loser['discord_user_id']}> to a game of:"
        f" {challenge_row['game_name']} "
        f"with {winner['score']}pts to {loser['score']}pts"
    )
    logger.info(string_me)
    params = {"discord_id": winner["discord_user_id"], "id": challenge_row["id"]}
    _ = db.execute(query=UPDATE_CHALLENGE_WINNER, args=params)
    rd_con = redis.Redis(host=os.getenv("REDIS_HOST"), port=6379, db=0)
    rd_con.publish("community-message", string_me)
    return


def post_score_action(db: PostgreSQLConnector, challenge_row_id: int):
    """

    Parameters
    ----------
    db: PostgreSQLConnector
    challenge_row_id: int
    """
    params = {"challenge_id": challenge_row_id}

    challenge_row = db.select_dataframe(query=CHALLENGE_BY_CHALLENGE_ID, args=params)

    if challenge_row.empty:
        return False

    challenge_row = challenge_row.to_dict("records")[0]

    if not challenge_row["challenger_score_id"] or not challenge_row["challengee_score_id"]:
        return False

    challenger_score_params = {"score_id": challenge_row["challenger_score_id"]}
    challengee_score_params = {"score_id": challenge_row["challengee_score_id"]}

    challenger_score_value = db.select_dataframe(query=SCORE_BY_SCORE_ID_QRY, args=challenger_score_params)
    challenger_score_value = challenger_score_value.to_dict("records")[0]

    challengee_score_value = db.select_dataframe(query=SCORE_BY_SCORE_ID_QRY, args=challengee_score_params)
    challengee_score_value = challengee_score_value.to_dict("records")[0]
    logger.info(challenger_score_value)
    logger.info(challengee_score_value)
    outcome_dict = set_outcome_dictionary(challenge_row, challenger_score_value, challengee_score_value)

    process_winner_loser(db, outcome_dict["winner"], outcome_dict["loser"], challenge_row)


def get_score_by_score_id(db: PostgreSQLConnector, score_id: int) -> pandas.DataFrame:
    """

    Parameters
    ----------
    db: PostgreSQLConnector
    score_id: int

    Returns
    -------
    pandas.DataFrame
    """
    logger.info(f"Retrieving score row by score id: {score_id}")
    score_results = db.select_dataframe(query=SCORE_BY_SCORE_ID_QRY, args={"score_id": score_id})
    logger.info(score_results)
    return score_results


def process_challenge_score(db: PostgreSQLConnector, user_uuid: str, mac_address: str, score_id: int):
    """

    Parameters
    ----------
    db: PostgreSQLConnector
    user_uuid: str
    mac_address: str
    score_id: int
    """
    score_results = get_score_by_score_id(db, score_id)
    score_results = score_results.to_dict("records")[0]
    challenge_ids = update_challenge_row_submitted_score(db, user_uuid, mac_address, score_id, score_results.get("game_name"))
    logger.info(challenge_ids)
    if challenge_ids.get("challenger_row_id"):
        post_score_action(db, challenge_ids.get("challenger_row_id"))

    if challenge_ids.get("challengee_row_id"):
        post_score_action(db, challenge_ids.get("challengee_row_id"))
