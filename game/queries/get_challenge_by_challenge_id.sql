select gc.*,
cr_u.discord_user_id as challenger_discord_id,
ce_u.discord_user_id as challengee_discord_id
from game_challenge gc
join users cr_u on cr_u.discord_handle = gc.challenger
join users ce_u on ce_u.discord_handle = gc.challengee
where
	gc.id = %(challenge_id)s