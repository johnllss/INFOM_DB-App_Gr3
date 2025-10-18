USE dbgolf;

CREATE TABLE user (
	user_id 			BIGINT PRIMARY KEY AUTO_INCREMENT,
    first_name  		VARCHAR(100) NOT NULL,
    middle_name 		VARCHAR(100) NULL,
    last_name 			VARCHAR(100) NOT NULL,
    email				VARCHAR(255) NOT NULL UNIQUE,
    contact				VARCHAR(20) NULL,
    membership_tier 	ENUM('Bronze', 'Silver', 'Gold', 'Platinum', 'Diamon') DEFAULT 'Bronze',
    membership_start 	DATE,
    membership_end 		DATE,
    months_subscribed 	BIGINT,
    loyalty_points 		BIGINT DEFAULT 0
);

-- USERS who have just started
INSERT INTO user (first_name, last_name, email)
VALUES
	('Ramon', 'Biyaya', 'ramonbiyaya@gmail.com)',
	('Rex', 'Dimalanta', 'rexdimalanta@gmail.com');


-- USERS who have been golfing already w/ full details
INSERT INTO user (first_name, middle_name, last_name, email, contact, membership_tier, membership_start, membership_end, months_subscribed, loyalty_points)
VALUES
	('Sam', 'Concepcion', 'Liwanag', 'samliwanag@gmail.com', '09129299349', 'Silver', '2025-01-01', '2026-01-01', 9, 180);


-- USERS who have been golfing already without middle_name
INSERT INTO user (first_name, last_name, email, contact, membership_tier, membership_start, membership_end, months_subscribed, loyalty_points)
VALUES
	('John', 'Lenoba', 'john_lenoba@gmail.com', '09193229394', 'Diamond', '2020-01-01', '2026-01-01', 72, 5489);
    
    
-- USERS who decided to subscribe
UPDATE user
SET 
	membership_tier = 'Silver',
    membership_start = '2023-11-01',
    membership_end = '2024-11-01',
    months_subscribed = 12
WHERE email = 'ramonbiyaya@gmail.com';