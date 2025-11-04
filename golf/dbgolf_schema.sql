USE bdxiyb8jgtmepmiynhz9;

SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS payment;
DROP TABLE IF EXISTS item;
DROP TABLE IF EXISTS session_user;
DROP TABLE IF EXISTS golf_session;
DROP TABLE IF EXISTS staff;
DROP TABLE IF EXISTS cart;
DROP TABLE IF EXISTS user;

CREATE TABLE user (
    user_id             INT PRIMARY KEY AUTO_INCREMENT,
    first_name          VARCHAR(100) NOT NULL,
    last_name           VARCHAR(100) NOT NULL,
    email               VARCHAR(255) NOT NULL UNIQUE,
    hash                VARCHAR(255) NOT NULL,
    contact             VARCHAR(20),
    membership_tier     ENUM('Unsubscribed','Bronze','Silver','Gold','Platinum','Diamond') DEFAULT 'Unsubscribed' NOT NULL,
    membership_start    DATE,
    membership_end      DATE,
    months_subscribed   INT DEFAULT 0 NOT NULL,
    loyalty_points      INT DEFAULT 0 NOT NULL
);

CREATE TABLE cart (
    cart_id     INT PRIMARY KEY AUTO_INCREMENT,
    total_price DECIMAL(10,2) DEFAULT 0 NOT NULL,
    user_id     INT,
    CONSTRAINT fk_cart_user FOREIGN KEY (user_id)
        REFERENCES user(user_id)
        ON DELETE CASCADE
);

CREATE TABLE staff (
    staff_id    INT PRIMARY KEY AUTO_INCREMENT,
    name        VARCHAR(100) NOT NULL,
    email       VARCHAR(100) NOT NULL,
    contact     VARCHAR(20) NOT NULL,
    max_clients INT DEFAULT 1,
    role        ENUM('Caddie','Coach') NOT NULL,
    status      ENUM('Available', 'Occupied') NOT NULL DEFAULT 'Available',
    service_fee DECIMAL(8,2) NOT NULL
);

CREATE TABLE golf_session (
    session_id          INT PRIMARY KEY AUTO_INCREMENT,
    type                ENUM('Driving Range','Fairway'),
    holes               ENUM('Half 9','Full 18'),
    session_schedule    DATETIME NOT NULL,
    people_limit        INT,
    status              ENUM('Available','Fully Booked','Ongoing','Finished') NOT NULL,
    session_price       DECIMAL(10,2) DEFAULT 0
);

CREATE TABLE session_user (
    session_user_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id         INT,
    session_id      INT NOT NULL,
    coach_id        INT NULL,
    caddie_id       INT NULL,
    score_fairway   INT DEFAULT NULL,
    longest_range   INT DEFAULT NULL,
    buckets         INT,
    loyalty_earned  INT DEFAULT 0,
    UNIQUE (session_id, user_id),
    CONSTRAINT fk_user FOREIGN KEY (user_id)
        REFERENCES user(user_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_session FOREIGN KEY (session_id)
        REFERENCES golf_session(session_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_coach FOREIGN KEY (coach_id)
        REFERENCES staff(staff_id)
        ON DELETE SET NULL,
    CONSTRAINT fk_caddie FOREIGN KEY (caddie_id)
        REFERENCES staff(staff_id)
        ON DELETE SET NULL
);

CREATE TABLE item (
    item_id     INT PRIMARY KEY AUTO_INCREMENT,
    name        VARCHAR(100) NOT NULL,
    category    ENUM('Clubs','Balls','Bags','Apparel','Equipment','Miscellaneous'),
    type        ENUM('Sale','Rental') NOT NULL,
    quantity    INT DEFAULT 1 NOT NULL,
    price       DECIMAL(10,2) NOT NULL,
    cart_id     INT NULL,
    CONSTRAINT fk_item_cart FOREIGN KEY (cart_id)
        REFERENCES cart(cart_id)
        ON DELETE CASCADE
);

CREATE TABLE payment (
    payment_id          INT PRIMARY KEY AUTO_INCREMENT,
    total_price         DECIMAL(10,2) DEFAULT 0,
    date_paid           DATETIME NOT NULL,
    payment_method      ENUM('Cash','GCash','Credit Card') NOT NULL,
    status              ENUM('Pending','Paid') NOT NULL,
    discount_applied    DECIMAL(5,2) DEFAULT 0.0,
    user_id             INT NOT NULL,
    cart_id             INT,
    session_user_id     INT,
    CONSTRAINT fk_payment_user FOREIGN KEY (user_id)
        REFERENCES user(user_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_payment_cart FOREIGN KEY (cart_id)
        REFERENCES cart(cart_id)
        ON DELETE SET NULL,
    CONSTRAINT fk_payment_session_user FOREIGN KEY (session_user_id)
        REFERENCES session_user(session_user_id)
        ON DELETE SET NULL
);

SET FOREIGN_KEY_CHECKS = 1;
