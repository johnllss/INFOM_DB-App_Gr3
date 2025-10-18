USE dbgolf;

CREATE TABLE user (
	user_id 			BIGINT PRIMARY KEY auto_increment,
    first_name  		VARCHAR(100) NOT NULL,
    middle_name 		VARCHAR(100) NULL,
    last_name 			VARCHAR(100) NOT NULL,
    email				VARCHAR(255) NOT NULL UNIQUE,
    contact				VARCHAR(20) NULL,
    membership_tier 	ENUM('Bronze', 'Silver', 'Gold', 'Platinum', 'Diamon'),
    membership_start 	DATE,
    membership_end 		DATE,
    months_subscribed 	BIGINT,
    loyalty_points 		BIGINT DEFAULT 0
);

