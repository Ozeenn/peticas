ALTER TABLE `adoption_requests` ADD `cpf_hash` text;--> statement-breakpoint
CREATE INDEX `adoption_cpf_hash` ON `adoption_requests` (`cpf_hash`);