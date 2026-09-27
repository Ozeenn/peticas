CREATE TABLE `medical_records` (
	`id` text PRIMARY KEY NOT NULL,
	`cat_id` integer NOT NULL,
	`treatment_id` text,
	`kind` text NOT NULL,
	`data` text NOT NULL,
	`user_id` text NOT NULL,
	`created` integer NOT NULL,
	FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE INDEX `medical_cat_created` ON `medical_records` (`cat_id`,`created`);