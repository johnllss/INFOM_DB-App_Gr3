USE dbgolf;

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