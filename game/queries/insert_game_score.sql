INSERT INTO game_score (game_id, game_name, score, duration, user_uuid, user_mac_address)
VALUES (%(game_id)s, %(game)s, %(score)s, %(duration)s, %(uuid)s, %(mac_address)s) RETURNING id;