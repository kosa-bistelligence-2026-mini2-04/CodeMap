CREATE TABLE "chat" (
	"id" text PRIMARY KEY NOT NULL,
	"repository_id" text NOT NULL,
	"user_id" text NOT NULL,
	"title" text DEFAULT 'New conversation' NOT NULL,
	"bootstrap_context" text,
	"last_message_at" timestamp DEFAULT now() NOT NULL,
	"created_at" timestamp DEFAULT now() NOT NULL,
	"updated_at" timestamp DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "chat_message" (
	"id" text PRIMARY KEY NOT NULL,
	"chat_id" text NOT NULL,
	"role" text NOT NULL,
	"content" text NOT NULL,
	"status" text DEFAULT 'complete' NOT NULL,
	"error_message" text,
	"input_tokens" integer,
	"output_tokens" integer,
	"created_at" timestamp DEFAULT now() NOT NULL
);
--> statement-breakpoint
ALTER TABLE "repository" ADD COLUMN "code_areas" text;--> statement-breakpoint
ALTER TABLE "repository" ADD COLUMN "code_areas_computed_at" timestamp;--> statement-breakpoint
ALTER TABLE "chat" ADD CONSTRAINT "chat_repository_id_repository_id_fk" FOREIGN KEY ("repository_id") REFERENCES "public"."repository"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "chat" ADD CONSTRAINT "chat_user_id_user_id_fk" FOREIGN KEY ("user_id") REFERENCES "public"."user"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "chat_message" ADD CONSTRAINT "chat_message_chat_id_chat_id_fk" FOREIGN KEY ("chat_id") REFERENCES "public"."chat"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
CREATE INDEX "chat_repositoryId_idx" ON "chat" USING btree ("repository_id");--> statement-breakpoint
CREATE INDEX "chat_userId_idx" ON "chat" USING btree ("user_id");--> statement-breakpoint
CREATE INDEX "chat_lastMessageAt_idx" ON "chat" USING btree ("last_message_at");--> statement-breakpoint
CREATE INDEX "chat_message_chatId_idx" ON "chat_message" USING btree ("chat_id");--> statement-breakpoint
CREATE INDEX "chat_message_createdAt_idx" ON "chat_message" USING btree ("created_at");