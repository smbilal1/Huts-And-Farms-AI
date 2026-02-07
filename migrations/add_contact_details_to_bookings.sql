-- Migration: Add contact_details column to bookings table
-- Date: 2026-02-07
-- Description: Stores formatted contact information (name and CNIC) for each booking

ALTER TABLE bookings 
ADD COLUMN IF NOT EXISTS contact_details TEXT;

-- Add comment to column
COMMENT ON COLUMN bookings.contact_details IS 'Formatted contact details: Name and CNIC for booking reference';
