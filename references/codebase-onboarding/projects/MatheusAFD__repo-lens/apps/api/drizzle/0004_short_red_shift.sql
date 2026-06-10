CREATE TABLE "analysis_question" (
	"id" text PRIMARY KEY NOT NULL,
	"analysis_id" text NOT NULL,
	"user_id" text NOT NULL,
	"question" text NOT NULL,
	"answer" text,
	"created_at" timestamp DEFAULT now() NOT NULL
);
--> statement-breakpoint
ALTER TABLE "analysis_question" ADD CONSTRAINT "analysis_question_analysis_id_analysis_id_fk" FOREIGN KEY ("analysis_id") REFERENCES "public"."analysis"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "analysis_question" ADD CONSTRAINT "analysis_question_user_id_user_id_fk" FOREIGN KEY ("user_id") REFERENCES "public"."user"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
CREATE INDEX "analysis_question_analysisId_idx" ON "analysis_question" USING btree ("analysis_id");