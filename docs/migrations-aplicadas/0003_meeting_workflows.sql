CREATE TABLE message_jobs (
 id TEXT PRIMARY KEY,
 target TEXT NOT NULL,
 message TEXT NOT NULL,
 created INTEGER NOT NULL,
 sent INTEGER,
 attempts INTEGER NOT NULL DEFAULT 0,
 next_attempt INTEGER NOT NULL DEFAULT 0,
 last_error TEXT
);
--> statement-breakpoint
CREATE TABLE attachments (
 id TEXT PRIMARY KEY,
 owner_type TEXT NOT NULL,
 owner_id TEXT NOT NULL,
 name TEXT NOT NULL,
 mime TEXT NOT NULL,
 data TEXT NOT NULL,
 created INTEGER NOT NULL
);
--> statement-breakpoint
CREATE UNIQUE INDEX medical_scheduled_dose ON medical_records(treatment_id, json_extract(data, '$.scheduledAt')) WHERE kind='application' AND json_extract(data, '$.scheduledAt')<>'';
