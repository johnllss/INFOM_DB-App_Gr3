CREATE SCHEMA IF NOT EXISTS dbgolf;

USE dbgolf;

CREATE TABLE user (
	user_id 			BIGINT PRIMARY KEY AUTO_INCREMENT,
    first_name  		VARCHAR(100) NOT NULL,
    middle_name 		VARCHAR(100) NULL,
    last_name 			VARCHAR(100) NOT NULL,
    email				VARCHAR(255) NOT NULL UNIQUE,
    contact				VARCHAR(20) NULL,
    membership_tier 	ENUM('Unsubscribed', 'Bronze', 'Silver', 'Gold', 'Platinum', 'Diamond') DEFAULT 'Unsubscribed',
    membership_start 	DATE,
    membership_end 		DATE,
    months_subscribed 	BIGINT,
    loyalty_points 		BIGINT DEFAULT 0
);

CREATE TABLE payment (
	payment_id			BIGINT PRIMARY KEY AUTO_INCREMENT,
  	total_price			DECIMAL(8,2) NOT NULL,
 	date_paid			DATETIME, -- null = not yet paid
  	payment_method		ENUM('Cash on Delivery', 'GCash', 'Credit Card'),
  	status				ENUM('Cancelled', 'Pending', 'Paid'),
  	discount_applied	DECIMAL(1,2) DEFAULT 0.0,
  	FOREIGN KEY 		(user_id) REFERENCES user(user_id),
  	FOREIGN KEY 		(session_id) REFERENCES session(session_id),
  	FOREIGN KEY 		(cart_id) REFERENCES cart(cart_id)
);

CREATE TABLE staff (
  staff_id		BIGINT PRIMARY KEY AUTO_INCREMENT,
  name			VARCHAR(100) NOT NULL,
  email			VARCHAR(100) NOT NULL,
  contact		VARCHAR(20) NOT NULL,
  role			VARCHAR(50) NOT NULL,
  status		ENUM('Available', 'Occupied') NOT NULL DEFAULT 'Available',
  service_fee	DECIMAL(8,2) NOT NULL
);

CREATE TABLE session (
	session_id			BIGINT PRIMARY KEY AUTO_INCREMENT,
    type				ENUM('Driving Range', 'Fairway'),
    holes				ENUM('Half 9', 'Full 18') DEFAULT NULL,
    buckets				INT DEFAULT NULL,
    session_schedule	DATE NOT NULL,
    people_quantity		INT NOT NULL,
    status				ENUM('CONFIRMED','CANCELLED','ON GOING','FINISHED') NOT NULL,
    FOREIGN KEY			(payment_id)	REFERENCES payment(payment_id),
    FOREIGN KEY			(user_id)		REFERENCES user(user_id)
);

CREATE TABLE cart(
    cart_id         BIGINT PRIMARY KEY,
    items_price     DECIMAL(10, 2) DEFAULT 0 NOT NULL
);

CREATE TABLE item(
    item_id         BIGINT PRIMARY KEY AUTO_INCREMENT,
    name            VARCHAR(100) NOT NULL,
    type            ENUM() NOT NULL,
    quantity        INT DEFAULT(1) NOT NULL,
    price           DECIMAL(10, 2) NOT NULL,
    FOREIGN KEY     (cart_id)   REFERENCES cart(cart_id)

);


DELIMITER //

CREATE TRIGGER update_items_price
AFTER INSERT OR UPDATE OR DELETE FROM ON item
FOR EACH ROW 
BEGIN
    UPDATE cart
    SET items_price = (
        SELECT  SUM(price * quantity)
        FROM    item
        WHERE   cart_id = NEW.cart_id
    )
    WHERE   cart_id = NEW.cart_id;
END;
//

DELIMITER;