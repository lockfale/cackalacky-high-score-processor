select game_id, game_name, score, duration, user_uuid, user_mac_address
from game_score
where id = %(score_id)s