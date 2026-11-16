--
-- Add field due_at to servicerequest
--
ALTER TABLE `requests_app_servicerequest` ADD COLUMN `due_at` datetime(6) NULL;
--
-- Add field resolution_summary to servicerequest
--
ALTER TABLE `requests_app_servicerequest` ADD COLUMN `resolution_summary` longtext NOT NULL;
--
-- Create index req_status_due_idx on field(s) status, due_at of model servicerequest
--
CREATE INDEX `req_status_due_idx` ON `requests_app_servicerequest` (`status`, `due_at`);
