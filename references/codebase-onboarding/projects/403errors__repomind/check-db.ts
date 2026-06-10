import { prisma } from "./src/lib/db";

async function checkPosts() {
  const posts = await prisma.blogPost.findMany({
    select: {
      id: true,
      title: true,
      published: true,
      slug: true,
    }
  });
  console.log("Total posts:", posts.length);
  console.log(JSON.stringify(posts, null, 2));
}

checkPosts().catch(console.error);
