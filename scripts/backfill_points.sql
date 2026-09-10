-- 가입 시 points 행이 생성되지 않던 기간의 계정 백필 (J-01)
INSERT INTO points (id, user_id, balance, created_at, updated_at)
SELECT gen_random_uuid(), u.id, 0, now(), now()
FROM users u
LEFT JOIN points p ON p.user_id = u.id
WHERE p.id IS NULL;
