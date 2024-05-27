import logging
from typing import List

import pandas

from connectors.pgsql import PostgreSQLConnector
from game.sql_helper import open_sql_file
from utilities.achievements import Achievements
from utilities.process_ctf_action import ctf_action

logger = logging.getLogger("s3logger")


GAME_ABBREVIATION_MAP = {
    "BO": "Breakout",
    "LA": "Labyrinth",
    "RO": "Asteroids",
    "TT": "Tappytime",
}

GAME_ID_MAP = {
    "Breakout": 1,
    "Labyrinth": 2,
    "Asteroids": 3,
    "Tappytime": 5,
}

# current working directory is going to be the root of the project
SCORE_QRY = open_sql_file("game/queries/get_game_score_by_badge_id_and_game.sql")
GET_GAME_ID_QRY = open_sql_file("game/queries/get_game_id_by_game_name.sql")
INSERT_GAME_SCORE = open_sql_file("game/queries/insert_game_score.sql")
AROUND_THE_WORLD_COUNT = open_sql_file("game/queries/get_around_the_world_count.sql")


def check_around_the_world_completion(db: PostgreSQLConnector, user_uuid: str, mac_address: str) -> bool:
    """TODO

    Parameters
    ----------
    db: PostgreSQLConnector
    user_uuid: str
    mac_address: str

    Returns
    -------
    bool
    """
    params = {"user_uuid": user_uuid, "mac_address": mac_address}
    records = db.select_dataframe(query=AROUND_THE_WORLD_COUNT, args=params)
    records = records.to_dict("records")
    logger.info(records)
    unique_games_count = records[0]["unique_game_count"]
    unique_games_played = records[0]["unique_games_played"]
    return unique_games_count == unique_games_played


def get_new_game_score_list(db: PostgreSQLConnector, game_to_be: str, user_uuid: str, mac_address: str) -> pandas.DataFrame:
    """

    Parameters
    ----------
    db: PostgreSQLConnector
    game_to_be: str
    user_uuid: str
    mac_address: str

    Returns
    -------

    """
    current_game_score_list = db.select_dataframe(
        query=SCORE_QRY,
        args={
            "user_uuid": user_uuid,
            "mac_address": mac_address,
            "game": game_to_be,
        },
    )
    return current_game_score_list


def get_game_id(db: PostgreSQLConnector, game: str, game_id: int = None) -> int:
    """

    Parameters
    ----------
    db: PostgreSQLConnector
    game: str
    game_id: Opt[int]

    Returns
    -------
    int
    """
    if not game_id:
        game_id_record = db.select_dataframe(query=GET_GAME_ID_QRY, args={"game": game})
        if len(game_id_record) == 0:
            return -1

        game_id = game_id_record.to_dict("records")[0]["id"]

    return game_id


def process_high_score_dict(db: PostgreSQLConnector, user_uuid: str, mac_address: str, high_score: dict) -> bool:
    """

    Parameters
    ----------
    db: PostgreSQLConnector
    user_uuid: str
    mac_address: str
    high_score: dict

    Returns
    -------
    bool
    """
    current_game = ""
    current_game_id = None
    current_game_score_list = []
    try:
        score = high_score["s"]
        duration = high_score["d"]
        game = high_score["g"]
        logger.info(f"{game}")

        logger.info(f"Current game: {current_game} | game {game}")
        if game != current_game:
            logger.info(f"Setting current game to: {game}")
            current_game = game
            current_game_id = GAME_ID_MAP.get(current_game, 0)
            current_game_score_list = get_new_game_score_list(db, game, user_uuid, mac_address)

        exists = ((current_game_score_list["score"] == score) & (current_game_score_list["duration"] == duration)).any()
        logger.info(f"Does the pair ({score} | {duration}) exist? {exists}")

        if not exists:
            logger.info(current_game_id)
            return synchronous_insert_game_score(db, user_uuid, mac_address, game, score, duration, current_game_id)
    except Exception as e:
        logger.error(e)


def process_high_scores(db: PostgreSQLConnector, user_uuid: str, mac_address: str, high_scores: List):
    """

    Parameters
    ----------
    db: PostgreSQLConnector
    user_uuid: str
    mac_address: str
    high_scores: List

    Returns
    -------

    """
    if isinstance(high_scores[0], list):
        high_scores = transform_game_list(high_scores)

    sorted_games = sorted(high_scores, key=lambda x: x["g"])
    logger.info(sorted_games)
    for high_score_record in sorted_games:
        process_high_score_dict(db, user_uuid, mac_address, high_score_record)


def submit_around_the_world(db: PostgreSQLConnector, user_uuid: str, mac_address: str):
    """

    Parameters
    ----------
    db: PostgreSQLConnector
    user_uuid: str
    mac_address: str

    Returns
    -------

    """
    did_play_all_games = check_around_the_world_completion(db, user_uuid, mac_address)
    logger.info(did_play_all_games)
    if did_play_all_games:
        event_id = 17
        achievements = Achievements()
        response = ctf_action(db, user_uuid, mac_address, event_id, achievements.AROUND_THE_WORLD)

        logger.info(response)


def synchronous_insert_game_score(
    db: PostgreSQLConnector, user_uuid: str, mac_address: str, game: str, score: str, duration: str, game_id: int = None
) -> bool:
    """

    Parameters
    ----------
    db: PostgreSQLConnector
    user_uuid: str
    mac_address: str
    game: str
    score: str
    duration: str
    game_id: Opt[int]

    Returns
    -------

    """
    game_id = get_game_id(db, game, game_id)

    # TODO -> custom exception
    if game_id < 0:
        return False

    params = {"game_id": game_id, "uuid": user_uuid, "mac_address": mac_address, "game": game, "score": score, "duration": duration}
    logger.info(params)
    record_id = db.execute(query=INSERT_GAME_SCORE, args=params)
    response = {"status": "SUCCESS", "data": {"record_id": record_id}}
    logger.info(response)
    submit_around_the_world(db, user_uuid, mac_address)
    return True


def transform_game_list(data: List[List[any]]) -> List[dict]:
    """

    Parameters
    ----------
    data: List[List[any]]

    Returns
    -------
    List[dict]
    """
    transformed_from_list_of_list = transform_game_list_of_list_to_list_of_dict(data)
    transformed_data = transform_game_names(transformed_from_list_of_list)

    return transformed_data


def transform_game_list_of_list_to_list_of_dict(data: List[List[any]]) -> List[dict]:
    """

    Parameters
    ----------
    data: List[List[any]]

    Returns
    -------
    List[dict]
    """
    keys = ["g", "s", "d"]
    transformed_data = [{keys[i]: item for i, item in enumerate(sublist)} for sublist in data]

    return transformed_data


def transform_game_names(data: List[dict]) -> List[dict]:
    """

    Parameters
    ----------
    data: List[dict]

    Returns
    -------
    List[dict]
    """
    for high_score in data:
        high_score["g"] = GAME_ABBREVIATION_MAP.get(high_score["g"], high_score["g"])

    return data
