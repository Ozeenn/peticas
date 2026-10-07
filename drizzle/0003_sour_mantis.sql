CREATE TABLE IF NOT EXISTS `attachments` (
	`id` text PRIMARY KEY NOT NULL,
	`owner_type` text NOT NULL,
	`owner_id` text NOT NULL,
	`name` text NOT NULL,
	`mime` text NOT NULL,
	`data` text NOT NULL,
	`created` integer NOT NULL
);
--> statement-breakpoint
CREATE TABLE IF NOT EXISTS `message_jobs` (
	`id` text PRIMARY KEY NOT NULL,
	`target` text NOT NULL,
	`message` text NOT NULL,
	`created` integer NOT NULL,
	`sent` integer,
	`attempts` integer DEFAULT 0 NOT NULL,
	`next_attempt` integer DEFAULT 0 NOT NULL,
	`last_error` text
);
--> statement-breakpoint
ALTER TABLE `medical_records` ADD `scheduled_at` text;--> statement-breakpoint
DROP INDEX IF EXISTS `medical_scheduled_dose`;
--> statement-breakpoint
CREATE UNIQUE INDEX `medical_scheduled_dose` ON `medical_records` (`treatment_id`,`scheduled_at`) WHERE "medical_records"."kind"='application' AND "medical_records"."scheduled_at" IS NOT NULL;
