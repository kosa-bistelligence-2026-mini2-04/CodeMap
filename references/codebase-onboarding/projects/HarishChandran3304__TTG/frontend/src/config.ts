interface Config {
  API_URL: string;
  DISCORD_INVITE_LINK: string;
}

const productionConfig: Config = {
  API_URL: import.meta.env.VITE_API_URL || "wss://ttg-backend-734884490004.asia-south1.run.app",
  DISCORD_INVITE_LINK: import.meta.env.VITE_DISCORD_INVITE_LINK || "https://discord.gg/discord-invite"
};

const developmentConfig: Config = {
  API_URL: "ws://localhost:8000",
  DISCORD_INVITE_LINK: import.meta.env.VITE_DISCORD_INVITE_LINK || "https://discord.gg/discord-invite"
};

const config: Config = import.meta.env.PROD ? productionConfig : developmentConfig;

export default config;