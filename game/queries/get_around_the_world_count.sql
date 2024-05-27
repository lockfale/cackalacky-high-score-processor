WITH total_unique_games AS (
    SELECT count(*) AS unique_game_count FROM game_list
),
asteroids_score AS (
    SELECT
        case when count(*) > 0 then 1 else 0 end AS has_score_asteroid
    FROM
        game_score gs
    WHERE
        user_uuid = %(user_uuid)s
        AND user_mac_address = %(mac_address)s
        AND game_name = 'Asteroids'
),
tt_score AS (
    SELECT
        case when count(*) > 0  then 1 else 0 end AS has_score_tt
    FROM
        game_score gs
    WHERE
        user_uuid = %(user_uuid)s
        AND user_mac_address = %(mac_address)s
        AND game_name = 'Tappytime'
),
labyrinth_score AS (
    SELECT
        case when count(*) > 0  then 1 else 0 end AS has_score_labyrinth
    FROM
        game_score gs
    WHERE
        user_uuid = %(user_uuid)s
        AND user_mac_address = %(mac_address)s
        AND game_name = 'Labyrinth'
),
breakout_score AS (
    SELECT
        case when count(*) > 0  then 1 else 0 end AS has_score_breakout
    FROM
        game_score gs
    WHERE
        user_uuid = %(user_uuid)s
        AND user_mac_address = %(mac_address)s
        AND game_name = 'Breakout'
)
SELECT
    labyrinth_score.has_score_labyrinth +
        breakout_score.has_score_breakout +
        asteroids_score.has_score_asteroid + tt_score.has_score_tt as unique_games_played, total_unique_games.*
FROM
    total_unique_games,
    asteroids_score,
    tt_score,
    labyrinth_score,
    breakout_score;