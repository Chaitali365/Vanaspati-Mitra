-- 1. Create Database (if you haven't already)
CREATE DATABASE plantdb;

-- 2. Connect to the database (Run this if using command line: \c plantdb)

-- 3. Create the 'plant_logs' table
CREATE TABLE plant_logs (
    id SERIAL PRIMARY KEY,
    image_filename VARCHAR(255) NOT NULL,
    plant_name VARCHAR(255),
    probability FLOAT,
    captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
