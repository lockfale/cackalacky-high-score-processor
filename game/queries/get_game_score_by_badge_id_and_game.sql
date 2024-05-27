select game_id, score, duration
from game_score
where
    user_uuid = %(user_uuid)s
    and user_mac_address = %(mac_address)s
    and game_name = %(game)s
order by id desc
limit 10