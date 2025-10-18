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

-- USERS who have just 

-- VALUES with all columns
INSERT INTO user (first_name, middle_name, last_name, email, contact, membership_tier, membership_start, membership_end, months_subscribed, loyalty_points)
VALUES
	();
    
-- VALUES without middle_name column
INSERT INTO user (first_name, last_name, email, contact, membership_tier, membership_start, membership_end, months_subscribed, loyalty_points)
VALUES
	();
    
-- 