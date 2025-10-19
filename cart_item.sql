USE dbgolf;

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