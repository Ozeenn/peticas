import { sqliteTable, text, integer, uniqueIndex, index } from 'drizzle-orm/sqlite-core';
export const users = sqliteTable('users', {
 id:text('id').primaryKey(), name:text('name').notNull(), email:text('email').notNull(), password:text('password').notNull(), role:text('role').notNull().default('pending'), created:integer('created').notNull()
},t=>[uniqueIndex('users_email').on(t.email)]);
export const sessions = sqliteTable('sessions', { id:text('id').primaryKey(), userId:text('user_id').notNull().references(()=>users.id), expires:integer('expires').notNull() },t=>[index('sessions_expires').on(t.expires)]);
export const limits = sqliteTable('rate_limits', { key:text('key').primaryKey(), count:integer('count').notNull(), expires:integer('expires').notNull() });
export const settings = sqliteTable('settings', { key:text('key').primaryKey(), value:text('value').notNull(), version:integer('version').notNull().default(1) });
export const items = sqliteTable('items', {
 id:text('id').primaryKey(), name:text('name').notNull(), category:text('category').notNull(), unit:text('unit').notNull(), quantity:integer('quantity').notNull().default(0), minimum:integer('minimum').notNull().default(0), notes:text('notes').notNull().default(''), version:integer('version').notNull().default(1), created:integer('created').notNull(), updated:integer('updated').notNull()
});
export const movements = sqliteTable('movements', {
 id:text('id').primaryKey(), itemId:text('item_id').notNull().references(()=>items.id), delta:integer('delta').notNull(), reason:text('reason').notNull(), userId:text('user_id').notNull().references(()=>users.id), created:integer('created').notNull()
},t=>[index('movements_item_created').on(t.itemId,t.created)]);
export const purchases = sqliteTable('purchases', {
 id:text('id').primaryKey(), itemId:text('item_id').notNull().references(()=>items.id), quantity:integer('quantity').notNull(), due:text('due').notNull(), supplier:text('supplier').notNull().default(''), notes:text('notes').notNull().default(''), status:text('status').notNull().default('scheduled'), userId:text('user_id').notNull().references(()=>users.id), created:integer('created').notNull(), completed:integer('completed')
},t=>[index('purchases_status_due').on(t.status,t.due)]);
export const notifications = sqliteTable('notifications', {
 id:text('id').primaryKey(), kind:text('kind').notNull(), itemId:text('item_id').references(()=>items.id), purchaseId:text('purchase_id').references(()=>purchases.id), message:text('message').notNull(), created:integer('created').notNull(), resolved:integer('resolved')
},t=>[index('notifications_resolved_created').on(t.resolved,t.created)]);
export const reads = sqliteTable('notification_reads', { id:text('id').primaryKey(), notificationId:text('notification_id').notNull().references(()=>notifications.id), userId:text('user_id').notNull().references(()=>users.id) },t=>[uniqueIndex('reads_user_notification').on(t.userId,t.notificationId)]);
export const applications = sqliteTable('adoption_requests', { id:text('id').primaryKey(), tokenHash:text('token_hash').notNull(), cpfHash:text('cpf_hash'), data:text('data').notNull(), version:integer('version').notNull().default(1), created:integer('created').notNull() },t=>[uniqueIndex('adoption_token_hash').on(t.tokenHash),index('adoption_cpf_hash').on(t.cpfHash)]);
export const medicalRecords = sqliteTable('medical_records', { id:text('id').primaryKey(), catId:integer('cat_id').notNull(), treatmentId:text('treatment_id'), kind:text('kind').notNull(), data:text('data').notNull(), userId:text('user_id').notNull().references(()=>users.id), created:integer('created').notNull() },t=>[index('medical_cat_created').on(t.catId,t.created)]);
