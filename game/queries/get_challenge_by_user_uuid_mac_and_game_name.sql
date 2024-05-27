with challenger_match AS (
select u.mac_address, u.uuid, u.discord_user_id, gc.*
from game_challenge gc
JOIN users u on u.discord_handle = gc.challenger
    and u.uuid = %(uuid)s
    and u.mac_address = %(mac_address)s
where
    gc.game_name = %(game)s
    and gc.challenger_score_id is NULL
    and (gc.winner is NULL or gc.winner = '')
    and gc.active = 1
order by gc.id ASC
limit 1
), challengee_match AS (
select u.mac_address, u.uuid, u.discord_user_id, gc.*
from game_challenge gc
JOIN users u on u.discord_handle = gc.challengee
    and u.uuid = %(uuid)s
    and u.mac_address = %(mac_address)s
where
    gc.game_name = %(game)s
    and gc.challengee_score_id is NULL
    and (gc.winner is NULL or gc.winner = '')
    and gc.active = 1
order by gc.id ASC
limit 1
)
SELECT
    (SELECT id FROM challenger_match) as challenger_row_id_challenger,
    (SELECT id FROM challengee_match) as challenger_row_id_challengee;
