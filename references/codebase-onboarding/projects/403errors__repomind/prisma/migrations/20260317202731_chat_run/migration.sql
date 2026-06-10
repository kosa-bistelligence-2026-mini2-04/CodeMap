-- CreateEnum
CREATE TYPE "ChatRunStatus" AS ENUM ('RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED');

-- CreateTable
CREATE TABLE "ChatRun" (
    "id" TEXT NOT NULL,
    "actorId" TEXT NOT NULL,
    "userId" TEXT,
    "conversationKey" TEXT NOT NULL,
    "scope" TEXT NOT NULL,
    "owner" TEXT,
    "repo" TEXT,
    "username" TEXT,
    "clientRequestId" TEXT NOT NULL,
    "status" "ChatRunStatus" NOT NULL DEFAULT 'RUNNING',
    "partialText" TEXT NOT NULL DEFAULT '',
    "finalText" TEXT,
    "errorMessage" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "ChatRun_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "ChatRun_actorId_updatedAt_idx" ON "ChatRun"("actorId", "updatedAt" DESC);

-- CreateIndex
CREATE INDEX "ChatRun_conversationKey_updatedAt_idx" ON "ChatRun"("conversationKey", "updatedAt" DESC);

-- CreateIndex
CREATE UNIQUE INDEX "ChatRun_actorId_conversationKey_clientRequestId_key" ON "ChatRun"("actorId", "conversationKey", "clientRequestId");

-- AddForeignKey
ALTER TABLE "ChatRun" ADD CONSTRAINT "ChatRun_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User"("id") ON DELETE CASCADE ON UPDATE CASCADE;
