CREATE DATABASE IF NOT EXISTS `golf_db` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE `golf_db`;

-- ==========================================
-- 1. STANDALONE TABLES (Create these first)
-- ==========================================

-- Table structure for table `user`
DROP TABLE IF EXISTS `user`;
CREATE TABLE `user` (
  `user_id` int NOT NULL AUTO_INCREMENT,
  `first_name` varchar(100) NOT NULL,
  `last_name` varchar(100) NOT NULL,
  `email` varchar(255) NOT NULL,
  `hash` varchar(255) NOT NULL,
  `contact` varchar(20) DEFAULT NULL,
  `membership_tier` enum('Unsubscribed','Bronze','Silver','Gold','Platinum','Diamond') NOT NULL DEFAULT 'Unsubscribed',
  `membership_start` date DEFAULT NULL,
  `membership_end` date DEFAULT NULL,
  `loyalty_points` int NOT NULL DEFAULT '0',
  `is_admin` tinyint(1) NOT NULL DEFAULT '0',
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- Table structure for table `staff`
DROP TABLE IF EXISTS `staff`;
CREATE TABLE `staff` (
  `staff_id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `email` varchar(100) NOT NULL,
  `contact` varchar(20) NOT NULL,
  `max_clients` int DEFAULT '1',
  `role` enum('Caddie','Coach') NOT NULL,
  `status` enum('Available','Occupied') NOT NULL DEFAULT 'Available',
  `service_fee` decimal(8,2) NOT NULL,
  PRIMARY KEY (`staff_id`),
  KEY `idx_role` (`role`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- Table structure for table `golf_session`
DROP TABLE IF EXISTS `golf_session`;
CREATE TABLE `golf_session` (
  `session_id` int NOT NULL AUTO_INCREMENT,
  `type` enum('Driving Range','Fairway') DEFAULT NULL,
  -- FIXED: Changed to Upper Case to match HTML values
  `holes` enum('9 FRONT','9 BACK','FULL 18') DEFAULT NULL, 
  `session_schedule` datetime NOT NULL,
  `people_limit` int DEFAULT NULL,
  `status` enum('Available','Fully Booked','Ongoing','Finished') NOT NULL,
  `session_price` decimal(10,2) DEFAULT '0.00',
  PRIMARY KEY (`session_id`),
  KEY `idx_session_schedule` (`session_schedule`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- ==========================================
-- 2. DEPENDENT TABLES (Create these next)
-- ==========================================

-- Table structure for table `cart`
DROP TABLE IF EXISTS `cart`;
CREATE TABLE `cart` (
  `cart_id` int NOT NULL AUTO_INCREMENT,
  `total_price` decimal(10,2) NOT NULL DEFAULT '0.00',
  `user_id` int DEFAULT NULL,
  `status` enum('archived','active') NOT NULL DEFAULT 'active',
  PRIMARY KEY (`cart_id`),
  KEY `fk_cart_user` (`user_id`),
  CONSTRAINT `fk_cart_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- Table structure for table `item`
DROP TABLE IF EXISTS `item`;
CREATE TABLE `item` (
  `item_id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `category` enum('Clubs','Balls','Bags','Apparel','Equipment','Miscellaneous') DEFAULT NULL,
  `type` enum('Sale','Rental') NOT NULL DEFAULT 'Sale',
  `quantity` int NOT NULL DEFAULT '1',
  `price` decimal(10,2) NOT NULL,
  `cart_id` int DEFAULT NULL,
  PRIMARY KEY (`item_id`),
  KEY `fk_item_cart` (`cart_id`),
  KEY `idx_type_category` (`type`,`category`),
  CONSTRAINT `fk_item_cart` FOREIGN KEY (`cart_id`) REFERENCES `cart` (`cart_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- Table structure for table `session_user`
SET FOREIGN_KEY_CHECKS = 0;

-- 1. DROP AND RE-CREATE SESSION_USER (To fix the Unique constraint issue)
DROP TABLE IF EXISTS `session_user`;

CREATE TABLE `session_user` (
  `session_user_id` int NOT NULL AUTO_INCREMENT,
  `user_id` int DEFAULT NULL,
  `session_id` int NOT NULL,
  `coach_id` int DEFAULT NULL,
  `caddie_id` int DEFAULT NULL,
  `score_fairway` int DEFAULT NULL,
  `longest_range` int DEFAULT NULL,
  `buckets` int DEFAULT NULL,
  `status` enum('Cancelled','Pending','Confirmed') DEFAULT 'Pending',
  PRIMARY KEY (`session_user_id`),
  -- UNIQUE KEY REMOVED HERE
  KEY `fk_coach` (`coach_id`),
  KEY `fk_caddie` (`caddie_id`),
  KEY `idx_user_status` (`user_id`,`status`),
  CONSTRAINT `fk_caddie` FOREIGN KEY (`caddie_id`) REFERENCES `staff` (`staff_id`) ON DELETE SET NULL,
  CONSTRAINT `fk_coach` FOREIGN KEY (`coach_id`) REFERENCES `staff` (`staff_id`) ON DELETE SET NULL,
  CONSTRAINT `fk_session` FOREIGN KEY (`session_id`) REFERENCES `golf_session` (`session_id`) ON DELETE CASCADE,
  CONSTRAINT `fk_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- Table structure for table `payment`
DROP TABLE IF EXISTS `payment`;
CREATE TABLE `payment` (
  `payment_id` int NOT NULL AUTO_INCREMENT,
  `total_price` decimal(10,2) DEFAULT '0.00',
  `date_paid` datetime DEFAULT NULL,
  `payment_method` enum('Cash','GCash','Credit Card') NOT NULL,
  `status` enum('Pending','Paid') NOT NULL,
  -- FIXED: Increased precision to avoid crashes on high discounts
  `discount_applied` decimal(10,2) DEFAULT '0.00', 
  `user_id` int NOT NULL,
  `cart_id` int DEFAULT NULL,
  `session_user_id` int DEFAULT NULL,
  -- FIXED: Added transaction_ref for grouping history
  `transaction_ref` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`payment_id`),
  KEY `fk_payment_cart` (`cart_id`),
  KEY `fk_payment_session_user` (`session_user_id`),
  KEY `idx_user_status` (`user_id`,`status`),
  CONSTRAINT `fk_payment_cart` FOREIGN KEY (`cart_id`) REFERENCES `cart` (`cart_id`) ON DELETE SET NULL,
  CONSTRAINT `fk_payment_session_user` FOREIGN KEY (`session_user_id`) REFERENCES `session_user` (`session_user_id`) ON DELETE SET NULL,
  CONSTRAINT `fk_payment_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

SET GLOBAL event_scheduler = ON;

DROP EVENT IF EXISTS change_to_ongoing;

DELIMITER $$

CREATE EVENT change_to_ongoing
ON SCHEDULE EVERY 1 MINUTE
STARTS NOW()
DO
BEGIN
    -- 1. Start sessions that have reached their time
    UPDATE golf_session
    SET status = 'Ongoing'
    WHERE 
        status IN ('Available', 'Fully Booked') 
        AND session_schedule <= NOW();
        
    -- 2. Finish sessions that started 4 hours ago (Optional Cleanup)
    -- Assuming a golf session lasts roughly 4 hours
    UPDATE golf_session
    SET status = 'Finished'
    WHERE 
        status = 'Ongoing'
        AND session_schedule <= DATE_SUB(NOW(), INTERVAL 4 HOUR);
END $$

DELIMITER ;